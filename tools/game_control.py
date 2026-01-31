#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
游戏控制脚本 - 通过本地socket发送命令到游戏客户端

基础命令:
    python game_control.py reload [模块路径]   # 热更新模块 (默认 base.hotfresh)
    python game_control.py restart             # 重启游戏 (switch_level)
    python game_control.py enter               # 快速进入游戏
    python game_control.py run <脚本名>        # 执行 tools/ 下的 lua 脚本
    python game_control.py pet                 # 打开宠物测试界面
    python game_control.py goto                # 传送到演武场（战斗测试区域）

启动游戏:
    python game_control.py start               # 启动游戏客户端 (带控制台)
"""

import socket
import sys
import time
import subprocess
import os
import struct
import json
import re

HOST = '127.0.0.1'

# 日志文件路径
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '.log', 'lua_player01.log')

def get_log_mtime():
    """获取日志文件修改时间"""
    try:
        return os.path.getmtime(LOG_FILE)
    except:
        return 0

def wait_for_log_update(timeout=30, initial_mtime=None):
    """等待日志文件更新"""
    if initial_mtime is None:
        initial_mtime = get_log_mtime()

    start = time.time()
    while time.time() - start < timeout:
        current_mtime = get_log_mtime()
        if current_mtime > initial_mtime:
            return True
        time.sleep(0.5)
    return False
PORT = 65432
TIMEOUT = 5

# 游戏启动配置
GAME_EXE = r'd:\Y3\y3\games\2.0\game\Engine\Binaries\Win64\Game_x64h.exe'
GAME_ARGS = [
    '--dx11',
    '--start=Python',
    '--python-args=type@editor_game,subtype@editor_game,editor_map_path@d:\\Y3\\ORPG项目总包\\ORPG,level_id@129406483677115854938498460620380268465,release@true,lua_dummy@space,lua_wait_debugger@true',
    '--plugin-config=Plugins-PyQt',
    '--console',
    '--luaconsole'
]

def send_command(cmd, wait_log=False, log_timeout=30):
    """发送命令到游戏（带认证）

    Args:
        cmd: 要发送的命令
        wait_log: 是否等待日志更新确认执行
        log_timeout: 等待日志更新的超时时间(秒)
    """
    # 记录发送前的日志修改时间
    initial_mtime = get_log_mtime() if wait_log else None

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        s.connect((HOST, PORT))

        # 先发送认证信息
        auth = 'version=GM'.encode('utf-8')
        s.send(auth)
        time.sleep(0.3)  # 等待认证处理完成

        # 发送实际命令
        data = cmd.encode('utf-8')
        s.send(data)
        print(f'[OK] 已发送: {cmd}')

        # 保持连接一段时间确保消息被转发
        time.sleep(0.5)

        # 尝试接收响应
        try:
            s.settimeout(2)
            response = s.recv(1024).decode('utf-8', errors='ignore')
            if response:
                print(f'[响应] {response.strip()}')
        except socket.timeout:
            pass

        s.close()

        # 等待日志更新确认命令已执行
        if wait_log:
            print(f'[等待] 等待游戏执行...')
            if wait_for_log_update(log_timeout, initial_mtime):
                print(f'[OK] 命令已执行（日志已更新）')
            else:
                print(f'[警告] 等待超时，命令可能未执行')
                return False

        return True
    except ConnectionRefusedError:
        print('[错误] 连接被拒绝 - 请确认游戏已启动且本地服务端已开启')
        return False
    except socket.timeout:
        print('[错误] 连接超时')
        return False
    except Exception as e:
        print(f'[错误] {e}')
        return False

def reload(module='base.hotfresh'):
    """热更新模块"""
    return send_command(f"热更新('{module}')")

def run_lua_file(filename, wait_log=True):
    """执行tools目录下的lua脚本（通过热更新命令）

    Args:
        filename: 脚本名（不含.lua后缀）
        wait_log: 是否等待日志更新确认执行
    """
    # 构造模块路径（不带.lua后缀）
    lua_path = f"tools.{filename}"
    if lua_path.endswith('.lua'):
        lua_path = lua_path[:-4]
    return send_command(f"热更新('{lua_path}')", wait_log=wait_log)

def restart():
    """重启游戏（通过热更新restart_game.lua）"""
    return run_lua_file('restart_game')

def quick_enter():
    """快速进入游戏"""
    return run_lua_file('quick_enter')

def pet_test():
    """打开宠物测试界面"""
    return run_lua_file('pet_test')

def goto_training():
    """传送到演武场（战斗测试区域）"""
    return run_lua_file('goto_training')

def start_game():
    """启动游戏客户端（旧方法，不推荐）"""
    if not os.path.exists(GAME_EXE):
        print(f'[错误] 游戏可执行文件不存在: {GAME_EXE}')
        return False

    try:
        cmd = [GAME_EXE] + GAME_ARGS
        print(f'[启动] 正在启动游戏...')
        print(f'[命令] {GAME_EXE}')
        for arg in GAME_ARGS:
            print(f'       {arg}')

        # 使用 Popen 在后台启动，不等待进程结束
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        print('[OK] 游戏启动命令已发送')
        print('[提示] 等待游戏窗口出现后，使用 "enter" 命令进入游戏')
        return True
    except Exception as e:
        print(f'[错误] 启动失败: {e}')
        return False

def read_helper_port():
    """读取 Y3 Helper 端口"""
    port_file = os.path.join(os.path.dirname(__file__), '..', 'log', 'helper_port.lua')
    try:
        with open(port_file, 'r') as f:
            match = re.search(r'return\s*(\d+)', f.read())
            if match:
                return int(match.group(1))
    except:
        pass
    return None

def send_y3helper(command, args=None):
    """发送命令到 Y3 Helper"""
    port = read_helper_port()
    if not port:
        print('[错误] 找不到 Y3 Helper 端口，请确认 Cursor/VSCode 已打开项目')
        return False

    try:
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
    except ConnectionRefusedError:
        print('[错误] Y3 Helper 连接被拒绝，请确认 Cursor/VSCode 已打开项目')
        return False
    except Exception as e:
        print(f'[错误] {e}')
        return False

def kill_game():
    """强制杀掉游戏进程（通过计划任务，有管理员权限）"""
    try:
        # 通过计划任务杀进程（管理员权限）
        result = subprocess.run(
            ['schtasks', '/run', '/tn', 'Y3KillGame'],
            capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            print('[OK] 已发送杀进程命令 (通过计划任务)')
            time.sleep(1)  # 等待进程被杀
            return True
        else:
            # 计划任务不存在，尝试直接杀（可能没权限）
            print('[警告] 计划任务Y3KillGame不存在，尝试直接杀进程...')
            result2 = subprocess.run(
                ['taskkill', '/F', '/IM', 'Game_x64h.exe'],
                capture_output=True, text=True, shell=True
            )
            if result2.returncode == 0:
                print('[OK] 已强制关闭游戏进程')
                return True
            elif '拒绝访问' in result2.stderr or 'Access' in result2.stderr:
                print('[错误] 权限不足，请先运行 setup_kill_task.bat 创建计划任务')
                return False
            else:
                print('[OK] 游戏进程未运行')
                return True
    except Exception as e:
        print(f'[警告] 杀进程失败: {e}')
        return True

def force_restart():
    """强制重启游戏：杀掉进程 -> 重新启动 -> 进入游戏"""
    print('[强制重启] 第1步: 杀掉游戏进程...')
    kill_game()
    time.sleep(2)  # 等待进程完全退出

    print('[强制重启] 第2步: 启动游戏...')
    if not launch_game():
        print('[错误] 启动游戏失败')
        return False

    print('[强制重启] 第3步: 等待游戏加载 (15秒)...')
    time.sleep(15)

    print('[强制重启] 第4步: 进入游戏...')
    quick_enter()

    print('[强制重启] 第5步: 等待进入游戏 (8秒)...')
    time.sleep(8)

    print('[OK] 强制重启完成!')
    return True

def launch_game():
    """通过计划任务启动游戏（无UAC弹窗）"""
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
            print('[提示] 请先运行 setup_no_uac.bat 创建计划任务')
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

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print('\n快捷命令:')
        print('  launch           - 启动游戏 (通过计划任务，无UAC弹窗)')
        print('  launch2          - 启动游戏 (通过Y3 Helper，会弹UAC)')
        print('  kill             - 强制杀掉游戏进程 (关闭Y3-Console)')
        print('  frestart         - 强制重启: 杀进程 -> 启动 -> 进入游戏')
        print('  start            - 启动游戏客户端 (旧方法，不推荐)')
        print('  reload [module]  - 热更新模块 (默认 base.hotfresh)')
        print('  restart          - 重启游戏 (switch_level，游戏卡死时无效)')
        print('  enter            - 快速进入游戏 (模拟点击开始)')
        print('  pet              - 打开宠物测试界面')
        print('  goto             - 传送到演武场（战斗测试区域）')
        print('  run <script>     - 执行 tools/ 下的 lua 脚本')
        print('\n选项:')
        print('  --no-wait        - 不等待日志更新确认')
        return

    # 检查是否有 --no-wait 选项
    wait_log = '--no-wait' not in sys.argv
    args = [a for a in sys.argv[1:] if a != '--no-wait']

    cmd = args[0].lower() if args else ''

    if cmd == 'kill':
        kill_game()
    elif cmd == 'frestart':
        force_restart()
    elif cmd == 'launch':
        launch_game()
    elif cmd == 'launch2':
        launch_game_y3helper()
    elif cmd == 'start':
        start_game()
    elif cmd == 'reload':
        module = args[1] if len(args) > 1 else 'base.hotfresh'
        reload(module)
    elif cmd == 'restart':
        restart()
    elif cmd == 'enter':
        quick_enter()
    elif cmd == 'pet':
        pet_test()
    elif cmd == 'goto':
        goto_training()
    elif cmd == 'run':
        if len(args) < 2:
            print('[错误] 请指定要执行的脚本名')
            return
        run_lua_file(args[1], wait_log=wait_log)
    else:
        # 直接发送原始命令
        raw_cmd = ' '.join(args)
        send_command(raw_cmd, wait_log=wait_log)

if __name__ == '__main__':
    main()
