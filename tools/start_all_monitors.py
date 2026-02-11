#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键启动所有监控器

同时启动：
1. file_listener.py - 监听 Y3 Helper 消息文件（捕获引擎异常）
2. log_listener.py - 监听游戏日志文件（捕获 Lua 层错误）
3. heartbeat_monitor.py - 心跳监控（检测卡死+自动恢复）
"""

import os
import sys
import subprocess
import time

def start_monitor(script_name, description):
    """启动监控脚本"""
    try:
        if sys.platform == 'win32':
            # Windows: 在新的 cmd 窗口中启动
            cmd = f'start "{description}" cmd /k "python {script_name}"'
            subprocess.Popen(cmd, shell=True)
        else:
            # Linux/Mac: 后台启动
            subprocess.Popen([sys.executable, script_name])

        print(f'[✓] {description} 已启动')
        return True
    except Exception as e:
        print(f'[✗] {description} 启动失败: {e}')
        return False

def main():
    print('=' * 60)
    print('Y3 游戏监控系统 - 一键启动')
    print('=' * 60)
    print()

    # 切换到 tools 目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    monitors = [
        ('file_listener.py', 'Y3 Helper 消息监听器'),
        ('log_listener.py', '游戏日志监听器'),
        ('heartbeat_monitor.py', '心跳监控器'),
    ]

    success_count = 0
    for script, desc in monitors:
        if os.path.exists(script):
            if start_monitor(script, desc):
                success_count += 1
                time.sleep(0.5)  # 避免窗口同时弹出
        else:
            print(f'[!] {desc} 文件不存在: {script}')

    print()
    print('=' * 60)
    print(f'启动完成：{success_count}/{len(monitors)} 个监控器已运行')
    print('=' * 60)
    print()
    print('监控说明：')
    print('  - Y3 Helper 消息监听器：捕获引擎级异常（如 nil 调用）')
    print('  - 游戏日志监听器：捕获 Lua 层错误（print/log 输出）')
    print('  - 心跳监控器：检测游戏冻结并自动 continue 恢复')
    print()
    print('所有监控器在独立窗口运行，关闭对应窗口即可停止')
    print()

if __name__ == '__main__':
    main()
    input('按 Enter 键退出...')
