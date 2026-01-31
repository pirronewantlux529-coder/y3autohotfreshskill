#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Y3 错误监听器 - 接收游戏端发来的错误消息

工作原理:
    1. 在本地启动一个监听服务器
    2. 游戏通过 tools.error_sender 模块连接并发送错误
    3. 监听器实时打印收到的错误消息

用法:
    python error_listener.py              # 启动监听器（默认端口12999）
    python error_listener.py --port 13000 # 使用指定端口

配合使用:
    1. 启动此监听器
    2. 在游戏中执行: _reloadlua('tools.error_sender')
    3. 之后所有错误会自动发送到监听器
"""

import socket
import struct
import json
import sys
import threading
import time
from datetime import datetime

DEFAULT_PORT = 12999

class ErrorListener:
    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self.running = False
        self.server = None
        self.clients = []

    def start(self):
        """启动监听服务器"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('127.0.0.1', self.port))
        self.server.listen(5)
        self.running = True

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 错误监听器已启动，端口: {self.port}")
        print(f"[提示] 在游戏中执行: _reloadlua('tools.error_sender')")
        print(f"[提示] 按 Ctrl+C 停止监听")
        print("-" * 60)

        while self.running:
            try:
                self.server.settimeout(1.0)
                try:
                    client, addr = self.server.accept()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 游戏已连接: {addr}")
                    self.clients.append(client)
                    # 启动线程处理此客户端
                    thread = threading.Thread(target=self.handle_client, args=(client, addr))
                    thread.daemon = True
                    thread.start()
                except socket.timeout:
                    continue
            except Exception as e:
                if self.running:
                    print(f"[错误] {e}")
                break

    def handle_client(self, client, addr):
        """处理客户端连接"""
        try:
            while self.running:
                # 读取4字节长度前缀
                header = self._recv_exact(client, 4)
                if not header:
                    break

                length = struct.unpack('>I', header)[0]
                if length > 1024 * 1024:  # 限制1MB
                    print(f"[警告] 消息过大: {length} bytes")
                    break

                # 读取消息体
                body = self._recv_exact(client, length)
                if not body:
                    break

                try:
                    data = json.loads(body.decode('utf-8'))
                    self.on_message(data)
                except json.JSONDecodeError as e:
                    print(f"[警告] JSON解析失败: {e}")

        except Exception as e:
            if self.running:
                print(f"[连接断开] {addr}: {e}")
        finally:
            try:
                client.close()
            except:
                pass
            if client in self.clients:
                self.clients.remove(client)

    def _recv_exact(self, sock, size):
        """精确接收指定字节数"""
        data = b''
        while len(data) < size:
            try:
                chunk = sock.recv(size - len(data))
                if not chunk:
                    return None
                data += chunk
            except:
                return None
        return data

    def on_message(self, data):
        """处理收到的消息"""
        msg_type = data.get('type', 'unknown')
        timestamp = data.get('timestamp', datetime.now().strftime('%H:%M:%S'))

        if msg_type == 'error':
            level = data.get('level', 'error')
            message = data.get('message', '')

            # 根据错误级别使用不同颜色
            color_map = {
                'fatal': '\033[91m',   # 红色
                'error': '\033[91m',   # 红色
                'warn': '\033[93m',    # 黄色
                'info': '\033[96m',    # 青色
                'debug': '\033[92m',   # 绿色
            }
            color = color_map.get(level, '')
            reset = '\033[0m' if color else ''

            print(f"[{timestamp}] {color}[{level.upper()}]{reset} {message}")

        elif msg_type == 'heartbeat':
            # 心跳消息，静默处理
            pass

        elif msg_type == 'connected':
            player = data.get('player', 'unknown')
            print(f"[{timestamp}] 玩家已连接: {player}")

        else:
            print(f"[{timestamp}] [{msg_type}] {data}")

    def stop(self):
        """停止监听"""
        self.running = False
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        if self.server:
            try:
                self.server.close()
            except:
                pass
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 监听器已停止")


def main():
    port = DEFAULT_PORT

    # 解析命令行参数
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == '--port' and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                print(f"[错误] 无效的端口号: {args[i + 1]}")
                return

    listener = ErrorListener(port)

    try:
        listener.start()
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()


if __name__ == '__main__':
    main()
