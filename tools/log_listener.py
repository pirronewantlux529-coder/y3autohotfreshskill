#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
游戏日志监听器 - 实时监控游戏 log 文件的新增内容

用法:
    python log_listener.py              # 监听默认日志文件
    python log_listener.py --file <路径>  # 监听指定日志文件
"""

import os
import sys
import time
import argparse

# ANSI 颜色
class Colors:
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def get_color(line):
    """根据日志内容返回颜色"""
    lower = line.lower()
    if '[error]' in lower or '[fatal]' in lower:
        return Colors.RED
    elif '[warn]' in lower or '[warning]' in lower:
        return Colors.YELLOW
    elif '[success]' in lower or '[ok]' in lower:
        return Colors.GREEN
    elif '[info]' in lower or '[debug]' in lower:
        return Colors.CYAN
    return ''

def tail_log(log_file, show_all=False):
    """持续监听日志文件新增内容

    Args:
        log_file: 日志文件路径
        show_all: 是否显示所有内容（否则只显示新增）
    """
    print(f'[监听] {log_file}')
    print('[提示] 只显示新增内容，按 Ctrl+C 停止')
    print('-' * 60)

    # 初始化读取位置
    if not show_all and os.path.exists(log_file):
        # 跳到文件末尾，只显示新增内容
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, 2)  # 跳到文件末尾
            last_pos = f.tell()
    else:
        last_pos = 0

    error_count = 0
    max_errors = 10

    while True:
        try:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        # 从上次位置继续读取
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()

                        # 显示新行
                        for line in new_lines:
                            line = line.rstrip('\n\r')
                            if not line.strip():
                                continue

                            # 应用颜色
                            color = get_color(line)
                            if color:
                                print(f'{color}{line}{Colors.RESET}')
                            else:
                                print(line)

                        # 成功读取，重置错误计数
                        error_count = 0

                except (PermissionError, IOError) as e:
                    # 文件被占用，等待后重试
                    error_count += 1
                    if error_count >= max_errors:
                        print(f'[严重错误] 连续 {max_errors} 次无法读取文件')
                        print(f'[错误详情] {e}')
                        break
                    time.sleep(1)
                    continue

            time.sleep(0.1)

        except KeyboardInterrupt:
            print('\n[停止]')
            break
        except Exception as e:
            print(f'[异常] {e}')
            error_count += 1
            if error_count >= max_errors:
                print(f'[严重错误] 连续 {max_errors} 次异常，退出')
                break
            time.sleep(1)

def main():
    # 启用 Windows 终端颜色
    if sys.platform == 'win32':
        os.system('')

    parser = argparse.ArgumentParser(description='游戏日志实时监听器')
    parser.add_argument('--file', '-f',
                       default=os.path.join(os.path.dirname(__file__), '..', '.log', 'lua_player01.log'),
                       help='日志文件路径')
    parser.add_argument('--all', '-a', action='store_true',
                       help='显示文件中的所有内容（不只是新增）')
    args = parser.parse_args()

    log_file = os.path.abspath(args.file)

    print('游戏日志监听器')
    print('=' * 60)
    tail_log(log_file, show_all=args.all)

if __name__ == '__main__':
    main()
