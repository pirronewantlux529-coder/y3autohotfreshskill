#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Y3 Helper 客户端库
提供与 Y3 Helper 通信的基础功能

使用示例：
    from y3helper_client import Y3HelperClient

    client = Y3HelperClient()
    client.reload_lua()  # 热更新
    client.run_lua("print('Hello!')")  # 执行 Lua 代码
    client.run_script("tools.my_test")  # 执行测试脚本
"""
import socket
import struct
import json
import os
import re

class Y3HelperClient:
    def __init__(self, port_file=None):
        """
        初始化客户端

        Args:
            port_file: helper_port.lua 文件路径，默认自动查找
        """
        self.port_file = port_file or self._find_port_file()
        self.msg_id = 0

    def _find_port_file(self):
        """查找 helper_port.lua 文件"""
        # 从当前目录向上查找
        current = os.path.dirname(os.path.abspath(__file__))
        for _ in range(10):
            port_file = os.path.join(current, 'log', 'helper_port.lua')
            if os.path.exists(port_file):
                return port_file
            # 也检查 script/log
            port_file = os.path.join(current, 'script', 'log', 'helper_port.lua')
            if os.path.exists(port_file):
                return port_file
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

        # 相对于脚本目录查找
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 如果在 .claude/skills/y3-game-test/examples 下
        possible = os.path.join(script_dir, '..', '..', '..', '..', 'log', 'helper_port.lua')
        if os.path.exists(possible):
            return os.path.abspath(possible)

        raise FileNotFoundError("找不到 helper_port.lua，请确保游戏已启动")

    def _read_port(self):
        """读取 Y3 Helper 端口"""
        with open(self.port_file, 'r', encoding='utf-8') as f:
            match = re.search(r'return\s*(\d+)', f.read())
            if match:
                return int(match.group(1))
        raise ValueError("无法从 helper_port.lua 读取端口")

    def _encode(self, obj):
        """编码消息"""
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        return struct.pack('>I', len(data)) + data

    def _send_command(self, command, args=None, timeout=5):
        """
        发送命令到 Y3 Helper

        Args:
            command: VSCode 命令名
            args: 命令参数列表
            timeout: 超时时间（秒）

        Returns:
            响应消息列表
        """
        port = self._read_port()
        self.msg_id += 1

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(('127.0.0.1', port))

        msg = {
            'method': 'command',
            'id': self.msg_id,
            'params': {
                'command': command,
                'args': args or []
            }
        }
        sock.send(self._encode(msg))

        # 接收响应
        import time
        time.sleep(0.5)
        sock.setblocking(False)

        buffer = b''
        try:
            while True:
                data = sock.recv(4096)
                if data:
                    buffer += data
                else:
                    break
        except:
            pass

        sock.close()

        # 解码响应
        messages = []
        offset = 0
        while offset + 4 <= len(buffer):
            length = struct.unpack('>I', buffer[offset:offset+4])[0]
            if offset + 4 + length > len(buffer):
                break
            content = buffer[offset+4:offset+4+length].decode('utf-8')
            try:
                messages.append(json.loads(content))
            except:
                pass
            offset += 4 + length

        return messages

    def reload_lua(self):
        """触发 Lua 热更新 (.rd)"""
        return self._send_command('y3-helper.reloadLua')

    def run_lua(self, code):
        """
        执行 Lua 代码

        Args:
            code: Lua 代码字符串
        """
        return self._send_command('y3-helper.runLua', [code])

    def run_script(self, module_name):
        """
        执行指定的 Lua 模块

        Args:
            module_name: 模块名，如 'tools.my_test'
        """
        code = f"_reloadlua('{module_name}')"
        return self.run_lua(code)


# 便捷函数
def reload_lua():
    """快速热更新"""
    return Y3HelperClient().reload_lua()

def run_lua(code):
    """快速执行 Lua 代码"""
    return Y3HelperClient().run_lua(code)

def run_script(module_name):
    """快速执行测试脚本"""
    return Y3HelperClient().run_script(module_name)


if __name__ == '__main__':
    import sys

    client = Y3HelperClient()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python y3helper_client.py reload       # 热更新")
        print("  python y3helper_client.py run <code>   # 执行 Lua 代码")
        print("  python y3helper_client.py script <mod> # 执行模块")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'reload':
        print("执行热更新...")
        client.reload_lua()
        print("完成")
    elif cmd == 'run' and len(sys.argv) > 2:
        code = ' '.join(sys.argv[2:])
        print(f"执行: {code}")
        client.run_lua(code)
        print("完成")
    elif cmd == 'script' and len(sys.argv) > 2:
        module = sys.argv[2]
        print(f"执行模块: {module}")
        client.run_script(module)
        print("完成")
    else:
        print("参数错误")
        sys.exit(1)
