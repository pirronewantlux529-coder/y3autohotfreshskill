#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
给 Y3 Helper 打补丁（HTTP 版本）

使用 HTTP 请求而不是原始 socket，因为 VSCode 扩展环境可能限制 net 模块
"""

import os
import re
import glob
import shutil
from datetime import datetime

# 监听器端口
LISTENER_PORT = 12999

def find_y3helper_extension():
    """查找 Y3 Helper 扩展路径"""
    patterns = [
        os.path.expanduser("~/.cursor/extensions/sumneko.y3-helper-*"),
        os.path.expanduser("~/.vscode/extensions/sumneko.y3-helper-*"),
        "C:/Users/*/.cursor/extensions/sumneko.y3-helper-*",
        "C:/Users/*/.vscode/extensions/sumneko.y3-helper-*",
    ]

    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return sorted(matches)[-1]

    return None

def remove_old_patch(content):
    """移除旧补丁"""
    # 移除从 FORWARD_TO_LISTENER 到 END FORWARD 的代码
    pattern = r'/\* FORWARD_TO_LISTENER.*?/\* END FORWARD \*/\s*'
    return re.sub(pattern, '', content, flags=re.DOTALL)

def patch_extension(ext_path):
    """给 extension.js 打补丁"""
    ext_js = os.path.join(ext_path, 'dist', 'extension.js')

    if not os.path.exists(ext_js):
        print(f'[错误] 找不到 extension.js: {ext_js}')
        return False

    # 读取文件
    with open(ext_js, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除旧补丁
    content = remove_old_patch(content)

    # 备份
    backup_path = ext_js + f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    shutil.copy(ext_js, backup_path)
    print(f'[备份] {backup_path}')

    # 查找 print 处理代码
    old_pattern = r'\(0,h\.registerMethod\)\("print",\(async\(e,t\)=>\{'

    # 新代码：使用 fetch API 或 http 模块
    # 改用更简单的方式：直接写文件让 Python 监听器读取
    forward_code = '''(0,h.registerMethod)("print",(async(e,t)=>{
/* FORWARD_TO_LISTENER - 转发消息到外部监听器 v2 */
try{
const fs=require("fs");
const path=require("path");
const msgFile=path.join(process.env.TEMP||"/tmp","y3helper_messages.jsonl");
const data=JSON.stringify({type:"print",level:t.message.match(/^\\[\\s*(.*?)\\]/)?.[1]||"info",message:t.message,timestamp:new Date().toISOString()})+"\\n";
fs.appendFileSync(msgFile,data);
}catch(err){}
/* END FORWARD */
'''

    match = re.search(old_pattern, content)
    if not match:
        print('[错误] 找不到要修改的代码模式')
        print('[提示] Y3 Helper 版本可能不兼容')
        return False

    # 替换
    new_content = content[:match.start()] + forward_code + content[match.end():]

    # 写回
    with open(ext_js, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print('[成功] 补丁已应用（文件版本）')
    print('[提示] 请重启 Cursor/VSCode 使补丁生效')
    print(f'[提示] 消息将写入: %TEMP%\\y3helper_messages.jsonl')
    return True

def main():
    print('Y3 Helper 消息转发补丁 (文件版本)')
    print('=' * 50)

    ext_path = find_y3helper_extension()
    if not ext_path:
        print('[错误] 找不到 Y3 Helper 扩展')
        print('[提示] 请确认已安装 Y3 Helper 扩展')
        return

    print(f'[找到] {ext_path}')
    patch_extension(ext_path)

if __name__ == '__main__':
    main()
