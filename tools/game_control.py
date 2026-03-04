#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
游戏控制脚本 - 通过 Y3 Helper 发送命令到游戏客户端

用法:
    python game_control.py launch              # 启动游戏（通过Y3 Helper）
    python game_control.py reload [模块路径]  # 热更新模块 (默认 base.hotfresh)
    python game_control.py restart             # 重启游戏 (tools.restart_game)
    python game_control.py kill                # 关闭游戏进程（权限不足自动回退计划任务）
    python game_control.py run <脚本名>        # 执行 tools/ 下的 lua 脚本（命令ID强校验）
    python game_control.py lua "代码"          # 执行任意 Lua 代码（命令ID强校验）
    python game_control.py c                   # 发送 continue（断点恢复）

说明:
    - `run/lua` 现在采用递增命令ID校验，必须命中 `[RUN-CMD-OK] id=N` 才判定成功。
    - 对 `run` 脚本可额外声明 `-- @run-success: xxx` 作为必达成功标记。
    - 工具默认不内置 `enter`，如项目需要请自行提供脚本并 `run`。
"""

import json
import os
import re
import socket
import struct
import subprocess
import sys
import time

from game_run_check import run_lua_with_checks, run_script_with_checks

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, '..', '.log', 'lua_player01.log')
MSG_FILE = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '/tmp')), 'y3helper_messages.jsonl')
RUN_ID_FILE = os.path.join(SCRIPT_DIR, '.run_cmd_id.txt')


def read_port():
    possible_paths = [
        'log/helper_port.lua',
        '../log/helper_port.lua',
        '../../log/helper_port.lua',
    ]
    project_path = os.environ.get('Y3_PROJECT_PATH')
    if project_path:
        possible_paths.insert(0, os.path.join(project_path, 'log', 'helper_port.lua'))

    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                match = re.search(r'return\s*(\d+)', f.read())
                if match:
                    return int(match.group(1))
    raise FileNotFoundError('找不到 helper_port.lua，请确认游戏已启动')


def send_y3helper(command, args=None):
    try:
        port = read_port()
        sock = socket.socket()
        sock.settimeout(5)
        sock.connect(('127.0.0.1', port))

        msg = {
            'method': 'command',
            'id': 1,
            'params': {'command': command, 'args': args or []},
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


def _run_subprocess(cmd):
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore',
        shell=True,
    )


def kill_game():
    result = _run_subprocess(['taskkill', '/F', '/IM', 'Game_x64h.exe'])
    if result.returncode == 0:
        print('[OK] 已关闭 Game_x64h.exe')
        return True

    err = (result.stderr or result.stdout or '').strip()
    denied = ('access is denied' in err.lower()) or ('拒绝访问' in err)
    if denied:
        print('[警告] taskkill 权限不足，尝试回退计划任务 Y3KillGame')
        fallback = _run_subprocess(['schtasks', '/run', '/tn', 'Y3KillGame'])
        if fallback.returncode == 0:
            print('[OK] 已发送 Y3KillGame 计划任务')
            time.sleep(1)
            return True
        ferr = (fallback.stderr or fallback.stdout or '').strip()
        print(f'[错误] 计划任务 Y3KillGame 执行失败: {ferr or "unknown error"}')
        return False

    not_found = ('not found' in err.lower()) or ('没有运行的实例' in err) or ('未找到' in err)
    if not_found:
        print('[跳过] 未检测到 Game_x64h.exe 运行实例')
        return True

    print(f'[错误] kill 失败: {err or "unknown error"}')
    return False


def _helper_ready():
    try:
        port = read_port()
        sock = socket.socket()
        sock.settimeout(2)
        sock.connect(('127.0.0.1', port))
        sock.close()
        return True, f'Y3 Helper 可连接 (port={port})'
    except Exception as e:
        return False, f'Y3 Helper 未就绪: {e}'


def launch_game():
    if send_y3helper('y3-helper.launchGame'):
        print('[OK] 游戏启动命令已发送')
        return True
    return False


def reload_lua(module='base.hotfresh'):
    if send_y3helper('y3-helper.reloadLua'):
        print(f'[OK] 热更新已发送 (module={module})')
        return True
    return False


def run_lua_code(code, timeout=10):
    return run_lua_with_checks(
        send_y3helper=send_y3helper,
        is_game_running=_helper_ready,
        log_file=LOG_FILE,
        msg_file=MSG_FILE,
        run_id_file=RUN_ID_FILE,
        code=code,
        timeout=timeout,
    )


def run_lua_file(filename):
    return run_script_with_checks(
        send_y3helper=send_y3helper,
        is_game_running=_helper_ready,
        script_dir=SCRIPT_DIR,
        log_file=LOG_FILE,
        msg_file=MSG_FILE,
        run_id_file=RUN_ID_FILE,
        filename=filename,
        expect_marker=None,
        timeout=None,
    )


def restart_game():
    return run_lua_file('restart_game')


def debug_continue():
    if send_y3helper('workbench.action.debug.continue'):
        print('[OK] 已发送继续运行命令')
        return True
    print('[错误] continue 发送失败')
    return False


def print_test():
    return run_lua_code("print('[测试] Hello from game_control.py!')")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print('\n可用命令:')
        print('  launch           - 启动游戏（通过 Y3 Helper）')
        print('  reload [module]  - 热更新模块 (默认 base.hotfresh)')
        print('  restart          - 重启游戏（tools.restart_game）')
        print('  kill             - 关闭游戏进程（权限不足自动回退计划任务）')
        print('  run <script>     - 执行 tools/ 下的 lua 脚本（命令ID强校验）')
        print('  lua "代码"       - 执行任意 Lua 代码（命令ID强校验）')
        print('  c                - 发送 continue（断点恢复）')
        print('  test             - 简单打印测试')
        return

    cmd = sys.argv[1].lower()

    if cmd in ('launch', 'start'):
        ok = launch_game()
    elif cmd == 'reload':
        module = sys.argv[2] if len(sys.argv) > 2 else 'base.hotfresh'
        ok = reload_lua(module)
    elif cmd == 'restart':
        ok = restart_game()
    elif cmd == 'kill':
        ok = kill_game()
    elif cmd == 'run':
        if len(sys.argv) < 3:
            print('[错误] 请指定要执行的脚本名')
            sys.exit(1)
        ok = run_lua_file(sys.argv[2])
    elif cmd == 'lua':
        if len(sys.argv) < 3:
            print('[错误] 请指定要执行的 Lua 代码')
            sys.exit(1)
        ok = run_lua_code(' '.join(sys.argv[2:]))
    elif cmd in ('continue', 'c'):
        ok = debug_continue()
    elif cmd == 'test':
        ok = print_test()
    else:
        ok = run_lua_code(' '.join(sys.argv[1:]))

    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
