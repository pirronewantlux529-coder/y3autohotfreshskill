#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
给 Y3 Helper 打补丁，让它把收到的消息转发到我们的监听器

用法:
    python patch_y3helper_forward.py

这个脚本会修改 Y3 Helper 的 extension.js，在处理 print 消息时
同时转发到 127.0.0.1:12999
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
            # 返回最新版本
            return sorted(matches)[-1]

    return None

def patch_extension(ext_path):
    """给 extension.js 打补丁"""
    ext_js = os.path.join(ext_path, 'dist', 'extension.js')

    if not os.path.exists(ext_js):
        print(f'[错误] 找不到 extension.js: {ext_js}')
        return False

    # 读取文件
    with open(ext_js, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经打过补丁
    if 'FORWARD_TO_LISTENER' in content:
        print('[跳过] 已经打过补丁')
        return True

    # 备份
    backup_path = ext_js + f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    shutil.copy(ext_js, backup_path)
    print(f'[备份] {backup_path}')

    # 查找 print 处理代码
    # 原始代码: (0,h.registerMethod)("print",(async(e,t)=>{let r=t.message.match...
    old_pattern = r'\(0,h\.registerMethod\)\("print",\(async\(e,t\)=>\{let r=t\.message\.match'

    # 新代码：添加转发逻辑
    forward_code = f'''(0,h.registerMethod)("print",(async(e,t)=>{{
/* FORWARD_TO_LISTENER - 转发消息到外部监听器 */
try{{
const net=require("net");
const sock=new net.Socket();
sock.setTimeout(100);
sock.connect({LISTENER_PORT},"127.0.0.1",()=>{{
const data=JSON.stringify({{type:"print",level:t.message.match(/^\\[\\s*(.*?)\\]/)?.[1]||"info",message:t.message,timestamp:new Date().toLocaleTimeString()}});
const len=Buffer.alloc(4);len.writeUInt32BE(Buffer.byteLength(data));
sock.write(Buffer.concat([len,Buffer.from(data)]));
sock.end();
}});
sock.on("error",()=>{{}});
}}catch(err){{}}
/* END FORWARD */
let r=t.message.match'''

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

    print('[成功] 补丁已应用')
    print('[提示] 请重启 Cursor/VSCode 使补丁生效')
    return True

def main():
    print('Y3 Helper 消息转发补丁')
    print('=' * 50)

    ext_path = find_y3helper_extension()
    if not ext_path:
        print('[错误] 找不到 Y3 Helper 扩展')
        print('[提示] 请确认已安装 Y3 Helper 扩展')
        return

    print(f'[找到] {ext_path}')

    if patch_extension(ext_path):
        print('')
        print('补丁说明:')
        print(f'  - Y3 Helper 收到的所有 print 消息会转发到 127.0.0.1:{LISTENER_PORT}')
        print('  - 运行 error_listener.py 即可接收')
        print('  - 包括引擎级错误（"发生异常"等）')

if __name__ == '__main__':
    main()
