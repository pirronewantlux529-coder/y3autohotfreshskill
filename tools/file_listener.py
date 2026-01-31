#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件监听器 - 监控 Y3 Helper 写入的消息文件

用法:
    python file_listener.py
"""

import os
import sys
import time
import json

# 消息文件路径
MSG_FILE = os.path.join(os.environ.get('TEMP', '/tmp'), 'y3helper_messages.jsonl')

# ANSI 颜色
class Colors:
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def get_color(level):
    level = (level or '').lower()
    if level in ('error', 'fatal'):
        return Colors.RED
    elif level == 'warn':
        return Colors.YELLOW
    elif level == 'info':
        return Colors.CYAN
    elif level == 'debug':
        return Colors.GREEN
    return Colors.RESET

def clear_file():
    """清空消息文件"""
    if os.path.exists(MSG_FILE):
        open(MSG_FILE, 'w').close()
        print(f'[清空] {MSG_FILE}')

def tail_file():
    """持续读取新消息"""
    print(f'[监听] {MSG_FILE}')
    print('[提示] 按 Ctrl+C 停止')
    print('-' * 50)

    # 清空旧消息
    clear_file()

    last_size = 0
    last_lines = 0

    while True:
        try:
            if os.path.exists(MSG_FILE):
                with open(MSG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                # 只处理新行
                if len(lines) > last_lines:
                    for line in lines[last_lines:]:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                            level = data.get('level', 'info')
                            message = data.get('message', '')
                            timestamp = data.get('timestamp', '')

                            color = get_color(level)
                            print(f'{color}[{timestamp}][{level}] {message}{Colors.RESET}')
                        except json.JSONDecodeError:
                            print(f'[RAW] {line}')

                    last_lines = len(lines)

            time.sleep(0.1)

        except KeyboardInterrupt:
            print('\n[停止]')
            break
        except Exception as e:
            print(f'[错误] {e}')
            time.sleep(1)

if __name__ == '__main__':
    # 启用 Windows 终端颜色
    if sys.platform == 'win32':
        os.system('')  # 启用 ANSI

    print('Y3 Helper 文件监听器')
    print('=' * 50)
    tail_file()
