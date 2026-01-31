#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
给 Y3 Helper 打补丁 - 捕获调试器异常事件

通过 VSCode 的 debug.registerDebugAdapterTrackerFactory 拦截调试器消息，
当检测到异常事件时，写入文件供外部监听。
"""

import os
import re
import glob
import shutil
from datetime import datetime

# 消息文件路径
MSG_FILE = os.path.join(os.environ.get('TEMP', '/tmp'), 'y3helper_messages.jsonl')

def find_y3helper_extension():
    """查找 Y3 Helper 扩展路径"""
    patterns = [
        os.path.expanduser("~/.cursor/extensions/sumneko.y3-helper-*"),
        os.path.expanduser("~/.vscode/extensions/sumneko.y3-helper-*"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return sorted(matches)[-1]
    return None

def patch_extension(ext_path):
    """给 extension.js 打补丁"""
    ext_js = os.path.join(ext_path, 'dist', 'extension.js')

    if not os.path.exists(ext_js):
        print(f'[错误] 找不到 extension.js: {ext_js}')
        return False

    with open(ext_js, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经打过这个补丁
    if 'DEBUG_EXCEPTION_TRACKER' in content:
        print('[跳过] 调试异常捕获补丁已存在')
        return True

    # 备份
    backup_path = ext_js + f'.backup.exception.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    shutil.copy(ext_js, backup_path)
    print(f'[备份] {backup_path}')

    # 找到 onDidStartDebugSession 的位置，在其后添加异常追踪器
    # 原代码: a.debug.onDidStartDebugSession((e=>{"y3lua"===e.type&&p.push(e)}))
    old_pattern = r'(a\.debug\.onDidStartDebugSession\(\(e=>\{"y3lua"===e\.type&&p\.push\(e\)\}\)\))'

    # 新代码：添加调试适配器追踪器（只捕获异常，不监听暂停状态）
    tracker_code = '''/* DEBUG_EXCEPTION_TRACKER - 捕获调试器异常 */
a.debug.registerDebugAdapterTrackerFactory("y3lua",{createDebugAdapterTracker:function(session){
return{onDidSendMessage:function(msg){
if(msg.type==="event"&&msg.event==="stopped"&&msg.body?.reason==="exception"){
try{
const fs=require("fs");
const path=require("path");
const msgFile=path.join(process.env.TEMP||"/tmp","y3helper_messages.jsonl");
const data=JSON.stringify({type:"exception",level:"error",message:msg.body.text||"Unknown exception",description:msg.body.description||"",threadId:msg.body.threadId,timestamp:new Date().toISOString()})+"\\n";
fs.appendFileSync(msgFile,data);
}catch(err){}
}
}};
}}),
/* END DEBUG_EXCEPTION_TRACKER */
'''

    match = re.search(old_pattern, content)
    if not match:
        print('[错误] 找不到要修改的代码模式 (onDidStartDebugSession)')
        print('[提示] Y3 Helper 版本可能不兼容')
        return False

    # 在 onDidStartDebugSession 之前插入追踪器
    new_content = content[:match.start()] + tracker_code + content[match.start():]

    with open(ext_js, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print('[成功] 调试异常捕获补丁已应用')
    print(f'[提示] 异常消息将写入: {MSG_FILE}')
    print('[提示] 请重启 Cursor/VSCode 使补丁生效')
    return True

def main():
    print('Y3 Helper 调试异常捕获补丁')
    print('=' * 50)

    ext_path = find_y3helper_extension()
    if not ext_path:
        print('[错误] 找不到 Y3 Helper 扩展')
        return

    print(f'[找到] {ext_path}')
    patch_extension(ext_path)

if __name__ == '__main__':
    main()
