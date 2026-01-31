#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
游戏控制脚本 - 通过 Y3 Helper 发送命令到游戏客户端

用法:
    python game_control.py launch              # 启动游戏（通过Y3 Helper）
    python game_control.py reload [模块路径]  # 热更新模块 (默认 base.hotfresh)
    python game_control.py restart            # 重启游戏 (switch_level)
    python game_control.py enter              # 快速进入游戏
    python game_control.py run <脚本名>       # 执行 tools/ 下的 lua 脚本
    python game_control.py lua "代码"         # 执行任意 Lua 代码

前提条件:
    1. Cursor/VSCode 已打开项目且 Y3 Helper 插件运行中
    2. 已运行 install_y3helper_runlua.py 安装 runLua 命令
"""

import socket
import struct
import json
import sys
import os
import re
import time

# 日志文件路径（相对于脚本目录）
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '.log', 'lua_player01.log')

def get_log_mtime():
    """获取日志文件修改时间"""
    try:
        return os.path.getmtime(LOG_FILE)
    except:
        return 0

def wait_for_log_update(timeout=30, initial_mtime=None):
    """等待日志文件更新，确认命令已执行"""
    if initial_mtime is None:
        initial_mtime = get_log_mtime()

    start = time.time()
    while time.time() - start < timeout:
        current_mtime = get_log_mtime()
        if current_mtime > initial_mtime:
            return True
        time.sleep(0.5)
    return False

def read_port():
    """读取 Y3 Helper 端口"""
    # 尝试多个可能的路径
    possible_paths = [
        'log/helper_port.lua',
        '../log/helper_port.lua',
        '../../log/helper_port.lua',
    ]

    # 如果设置了项目路径环境变量
    project_path = os.environ.get('Y3_PROJECT_PATH')
    if project_path:
        possible_paths.insert(0, os.path.join(project_path, 'log', 'helper_port.lua'))

    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                match = re.search(r'return\s*(\d+)', f.read())
                if match:
                    return int(match.group(1))

    raise FileNotFoundError("找不到 helper_port.lua，请确认游戏已启动")

def send_y3helper(command, args=None):
    """发送命令到 Y3 Helper"""
    try:
        port = read_port()
        sock = socket.socket()
        sock.settimeout(5)
        sock.connect(('127.0.0.1', port))

        msg = {
            'method': 'command',
            'id': 1,
            'params': {'command': command, 'args': args or []}
        }
        data = json.dumps(msg).encode('utf-8')
        sock.send(struct.pack('>I', len(data)) + data)
        sock.close()
        return True
    except FileNotFoundError as e:
        print(f'[错误] {e}')
        return False
    except ConnectionRefusedError:
        print('[错误] 连接被拒绝 - 请确认 Cursor/VSCode 已打开项目')
        return False
    except socket.timeout:
        print('[错误] 连接超时')
        return False
    except Exception as e:
        print(f'[错误] {e}')
        return False

def launch_game():
    """通过计划任务启动游戏（无UAC弹窗）"""
    import subprocess
    try:
        result = subprocess.run(
            ['schtasks', '/run', '/tn', 'Y3LaunchGame'],
            capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            print('[OK] 游戏启动命令已发送（通过计划任务，无UAC弹窗）')
            return True
        else:
            print(f'[错误] 计划任务执行失败: {result.stderr}')
            print('[提示] 请先按照 Y3_HELPER_SETUP.md 步骤5 创建计划任务')
            print('[提示] 或使用 launch2 通过 Y3 Helper 启动（会弹UAC）')
            return False
    except Exception as e:
        print(f'[错误] {e}')
        return False

def launch_game_y3helper():
    """通过 Y3 Helper 启动游戏（备用方式，会弹UAC）"""
    if send_y3helper('y3-helper.launchGame'):
        print('[OK] 游戏启动命令已发送（通过Y3 Helper）')
        return True
    return False

def reload_lua(module='base.hotfresh'):
    """热更新模块"""
    if send_y3helper('y3-helper.reloadLua'):
        print(f'[OK] 热更新已发送')
        return True
    return False

def run_lua_code(code):
    """执行任意 Lua 代码"""
    if send_y3helper('y3-helper.runLua', [code]):
        print(f'[OK] Lua 代码已发送')
        return True
    return False

def run_lua_file(filename, wait_log=True, log_timeout=30):
    """执行 tools 目录下的 Lua 脚本

    Args:
        filename: 脚本名（不含.lua后缀）
        wait_log: 是否等待日志更新确认执行
        log_timeout: 等待超时时间(秒)
    """
    # 记录发送前的日志修改时间
    initial_mtime = get_log_mtime() if wait_log else None

    lua_path = f"tools.{filename}"
    if lua_path.endswith('.lua'):
        lua_path = lua_path[:-4]
    code = f"_reloadlua('{lua_path}')"
    if send_y3helper('y3-helper.runLua', [code]):
        print(f'[OK] 执行脚本: {lua_path}')

        # 等待日志更新确认命令已执行
        if wait_log:
            print(f'[等待] 等待游戏执行...')
            if wait_for_log_update(log_timeout, initial_mtime):
                print(f'[OK] 命令已执行（日志已更新）')
                return True
            else:
                print(f'[警告] 等待超时，命令可能未执行')
                return False
        return True
    return False

def restart_game():
    """重启游戏"""
    return run_lua_file('restart_game')

def quick_enter():
    """快速进入游戏"""
    return run_lua_file('quick_enter')

def print_test():
    """简单打印测试"""
    return run_lua_code("print('[测试] Hello from game_control.py!')")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print('\n可用命令:')
        print('  launch           - 启动游戏（通过计划任务，无UAC弹窗）')
        print('  launch2          - 启动游戏（通过Y3 Helper，会弹UAC）')
        print('  reload [module]  - 热更新模块 (默认 base.hotfresh)')
        print('  restart          - 重启游戏')
        print('  enter            - 快速进入游戏')
        print('  run <script>     - 执行 tools/ 下的 lua 脚本')
        print('  lua "代码"       - 执行任意 Lua 代码')
        print('  test             - 简单打印测试')
        print('\n选项:')
        print('  --no-wait        - 不等待日志更新确认')
        return

    # 检查是否有 --no-wait 选项
    wait_log = '--no-wait' not in sys.argv
    args = [a for a in sys.argv[1:] if a != '--no-wait']

    cmd = args[0].lower() if args else ''

    if cmd == 'launch':
        launch_game()
    elif cmd == 'launch2' or cmd == 'start':
        launch_game_y3helper()
    elif cmd == 'reload':
        module = args[1] if len(args) > 1 else 'base.hotfresh'
        reload_lua(module)
    elif cmd == 'restart':
        restart_game()
    elif cmd == 'enter':
        quick_enter()
    elif cmd == 'run':
        if len(args) < 2:
            print('[错误] 请指定要执行的脚本名')
            return
        run_lua_file(args[1], wait_log=wait_log)
    elif cmd == 'lua':
        if len(args) < 2:
            print('[错误] 请指定要执行的 Lua 代码')
            return
        run_lua_code(args[1])
    elif cmd == 'test':
        print_test()
    else:
        # 尝试作为 Lua 代码执行
        raw_cmd = ' '.join(args)
        run_lua_code(raw_cmd)

if __name__ == '__main__':
    main()
