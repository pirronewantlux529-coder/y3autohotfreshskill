#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Y3 Helper 使用示例
展示如何通过 Y3 Helper 执行各种操作

运行方式（在 script 目录或其子目录下）：
    # Windows
    python .claude/skills/y3-game-test/examples/example_test.py

    # WSL (需要用 Windows Python 才能连接 Windows 端口)
    /mnt/c/Windows/py.exe .claude/skills/y3-game-test/examples/example_test.py
"""
import socket
import struct
import json
import os
import re
import time

# ========== 基础配置 ==========

def find_port_file():
    """查找 helper_port.lua 文件"""
    # 从当前脚本位置向上查找
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        # 检查 log/helper_port.lua
        port_file = os.path.join(current, 'log', 'helper_port.lua')
        if os.path.exists(port_file):
            return port_file
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    raise FileNotFoundError("找不到 log/helper_port.lua")

def read_port():
    """读取 Y3 Helper 端口"""
    port_file = find_port_file()
    with open(port_file, 'r', encoding='utf-8') as f:
        match = re.search(r'return\s*(\d+)', f.read())
        return int(match.group(1)) if match else None

def encode(obj):
    """编码消息"""
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    return struct.pack('>I', len(data)) + data

def send_command(command, args=None):
    """发送命令并返回响应"""
    port = read_port()
    sock = socket.socket()
    sock.connect(('127.0.0.1', port))

    msg = {
        'method': 'command',
        'id': 1,
        'params': {
            'command': command,
            'args': args or []
        }
    }
    sock.send(encode(msg))

    time.sleep(1)
    sock.setblocking(False)
    buf = b''
    try:
        while True:
            d = sock.recv(4096)
            if d:
                buf += d
            else:
                break
    except:
        pass

    sock.close()
    return buf

# ========== 便捷函数 ==========

def reload_lua():
    """触发热更新 .rd"""
    print("[Y3 Helper] 触发热更新...")
    send_command('y3-helper.reloadLua')
    print("[Y3 Helper] 热更新完成")

def run_lua(code):
    """执行 Lua 代码"""
    print(f"[Y3 Helper] 执行: {code[:50]}...")
    send_command('y3-helper.runLua', [code])
    print("[Y3 Helper] 执行完成")

def run_script(module_name):
    """执行测试脚本"""
    print(f"[Y3 Helper] 加载模块: {module_name}")
    run_lua(f"_reloadlua('{module_name}')")

# ========== 示例 ==========

if __name__ == '__main__':
    print("=" * 50)
    print("Y3 Helper 示例")
    print("=" * 50)

    port = read_port()
    print(f"Y3 Helper 端口: {port}")

    # 示例 1: 执行简单的 print
    print("\n--- 示例 1: 执行 print ---")
    run_lua("print('[Python] Hello from Y3 Helper!')")

    # 示例 2: 执行表达式
    print("\n--- 示例 2: 执行表达式 ---")
    run_lua("print('1 + 2 = ' .. tostring(1 + 2))")

    # 示例 3: 热更新
    print("\n--- 示例 3: 热更新 ---")
    reload_lua()

    # 示例 4: 执行测试脚本（如果存在）
    # print("\n--- 示例 4: 执行测试脚本 ---")
    # run_script("tools.my_test")

    print("\n" + "=" * 50)
    print("示例完成！请检查游戏日志确认执行结果")
    print("日志文件: script/.log/lua_player01.log")
    print("=" * 50)
