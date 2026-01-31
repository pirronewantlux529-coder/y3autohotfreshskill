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

def is_game_running():
    """检查游戏是否在运行（Game_x64h 且有 conhost 子进程）

    Returns:
        tuple: (是否运行, 详情消息)
    """
    try:
        # 获取 Game_x64h 进程ID
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-Process Game_x64h -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'],
            capture_output=True, text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            return False, 'Game_x64h 进程不存在'

        game_pids = result.stdout.strip().split()

        # 检查每个 Game_x64h 是否有 conhost 子进程
        for game_pid in game_pids:
            result2 = subprocess.run(
                ['powershell', '-Command',
                 f"Get-WmiObject Win32_Process -Filter \"ParentProcessId={game_pid} AND Name='conhost.exe'\" | Select-Object -ExpandProperty ProcessId"],
                capture_output=True, text=True
            )
            if result2.stdout.strip():
                return True, f'游戏运行中 (PID: {game_pid})'

        return False, 'Game_x64h 存在但无 conhost 子进程（可能未完全启动）'

    except Exception as e:
        return False, str(e)

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

# 不带调试器的启动参数（用于批量测试，错误会写入日志）
GAME_ARGS_NO_DEBUG = [
    '--dx11',
    '--start=Python',
    '--python-args=type@editor_game,subtype@editor_game,editor_map_path@d:\\Y3\\ORPG项目总包\\ORPG,level_id@129406483677115854938498460620380268465,release@true,lua_dummy@space,lua_wait_debugger@false',
    '--plugin-config=Plugins-PyQt',
    '--console',
    '--luaconsole'
]

# 带调试器的启动参数（用于调试，错误会在 Cursor 中定位）
GAME_ARGS_DEBUG = [
    '--dx11',
    '--start=Python',
    '--python-args=type@editor_game,subtype@editor_game,editor_map_path@d:\\Y3\\ORPG项目总包\\ORPG,level_id@129406483677115854938498460620380268465,release@true,lua_dummy@space,lua_wait_debugger@true',
    '--plugin-config=Plugins-PyQt',
    '--console',
    '--luaconsole'
]

# 默认使用不带调试器的参数
GAME_ARGS = GAME_ARGS_NO_DEBUG

def send_command(cmd, wait_log=False, log_timeout=30, check_game=True):
    """发送命令到游戏（带认证）

    Args:
        cmd: 要发送的命令
        wait_log: 是否等待日志更新确认执行
        log_timeout: 等待日志更新的超时时间(秒)
        check_game: 是否先检查游戏运行状态
    """
    # 先检查游戏是否在运行
    if check_game:
        running, msg = is_game_running()
        if not running:
            print(f'[错误] 游戏未运行: {msg}')
            return False

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

def run_lua_code(code, wait_log=True, safe_mode=True):
    """执行任意Lua代码（创建临时文件后热更新）

    Args:
        code: Lua代码字符串
        wait_log: 是否等待日志更新确认执行
        safe_mode: 是否用 pcall 包装（捕获错误写入日志，而不是弹窗）
    """
    import uuid

    # 获取tools目录
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(tools_dir, 'temp')
    os.makedirs(temp_dir, exist_ok=True)

    # 清理旧的临时文件（超过1分钟的）
    try:
        for f in os.listdir(temp_dir):
            if f.startswith('_temp_'):
                fp = os.path.join(temp_dir, f)
                if time.time() - os.path.getmtime(fp) > 60:
                    os.remove(fp)
    except:
        pass

    # 创建唯一文件名
    temp_name = f'_temp_{uuid.uuid4().hex[:8]}'
    temp_file = os.path.join(temp_dir, f'{temp_name}.lua')

    # 写入临时文件
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(f'-- 临时执行脚本\n')
        if safe_mode:
            # 用 xpcall 包装，错误写入日志而不是弹窗
            # 注意：引擎级错误（调用nil方法）无法被pcall捕获
            f.write('local ok, err = xpcall(function()\n')
            f.write(code)
            f.write('\nend, function(e) return debug.traceback(e) end)\n')
            f.write('if not ok then\n')
            f.write('    log.error("[临时脚本错误] " .. tostring(err))\n')
            f.write('end\n')
        else:
            f.write(code)
            f.write('\n')

    # 通过热更新执行（不立即删除文件，让游戏有时间读取）
    lua_path = f'tools.temp.{temp_name}'
    result = send_command(f"热更新('{lua_path}')", wait_log=wait_log)
    return result

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

def debug_continue():
    """让卡在断点/异常的游戏继续运行"""
    if send_y3helper('workbench.action.debug.continue'):
        print('[OK] 已发送继续运行命令')
        return True
    return False

def debug_pause():
    """暂停游戏（触发断点）"""
    if send_y3helper('workbench.action.debug.pause'):
        print('[OK] 已发送暂停命令')
        return True
    return False

def debug_step_over():
    """单步跳过"""
    if send_y3helper('workbench.action.debug.stepOver'):
        print('[OK] 单步跳过')
        return True
    return False

def debug_step_into():
    """单步进入"""
    if send_y3helper('workbench.action.debug.stepInto'):
        print('[OK] 单步进入')
        return True
    return False

def debug_step_out():
    """单步跳出"""
    if send_y3helper('workbench.action.debug.stepOut'):
        print('[OK] 单步跳出')
        return True
    return False

def show_status():
    """显示游戏运行状态"""
    running, msg = is_game_running()
    if running:
        print(f'[游戏] 运行中 - {msg}')
    else:
        print(f'[游戏] 未运行 - {msg}')

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print('\n快捷命令:')
        print('  status           - 检查游戏运行状态')
        print('  launch           - 启动游戏 (通过计划任务，无UAC弹窗)')
        print('  launch2          - 启动游戏 (通过Y3 Helper，会弹UAC)')
        print('  kill             - 强制杀掉游戏进程 (关闭Y3-Console)')
        print('  frestart         - 强制重启: 杀进程 -> 启动 -> 进入游戏')
        print('  continue / c     - 继续运行（从异常/断点恢复）')
        print('  pause / p        - 暂停游戏（触发断点）')
        print('  stepover / n     - 单步跳过')
        print('  stepinto / s     - 单步进入')
        print('  stepout / o      - 单步跳出')
        print('  break "代码"     - 在代码前插入断点执行')
        print('  start            - 启动游戏客户端 (旧方法，不推荐)')
        print('  reload [module]  - 热更新模块 (默认 base.hotfresh)')
        print('  restart          - 重启游戏 (switch_level，游戏卡死时无效)')
        print('  enter            - 快速进入游戏 (模拟点击开始)')
        print('  pet              - 打开宠物测试界面')
        print('  goto             - 传送到演武场（战斗测试区域）')
        print('  run <script>     - 执行 tools/ 下的 lua 脚本')
        print('  lua "代码"       - 执行任意 Lua 代码')
        print('\n选项:')
        print('  --no-wait        - 不等待日志更新确认')
        return

    # 检查是否有 --no-wait 选项
    wait_log = '--no-wait' not in sys.argv
    args = [a for a in sys.argv[1:] if a != '--no-wait']

    cmd = args[0].lower() if args else ''

    if cmd == 'status':
        show_status()
    elif cmd == 'kill':
        kill_game()
    elif cmd == 'frestart':
        force_restart()
    elif cmd == 'launch':
        launch_game()
    elif cmd == 'launch2':
        launch_game_y3helper()
    elif cmd == 'start':
        launch_game()  # start 等于 launch
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
    elif cmd == 'lua':
        if len(args) < 2:
            print('[错误] 请指定要执行的 Lua 代码')
            return
        code = ' '.join(args[1:])
        run_lua_code(code, wait_log=wait_log)
    elif cmd == 'continue' or cmd == 'c':
        debug_continue()
    elif cmd == 'pause' or cmd == 'p':
        debug_pause()
    elif cmd == 'stepover' or cmd == 'n':
        debug_step_over()
    elif cmd == 'stepinto' or cmd == 's':
        debug_step_into()
    elif cmd == 'stepout' or cmd == 'o':
        debug_step_out()
    elif cmd == 'break':
        # 在代码中插入断点：执行 dbg() 会触发断点
        if len(args) < 2:
            print('[提示] 在 Lua 代码中调用 dbg() 可触发断点')
            print('[示例] python game_control.py lua "dbg(); print(123)"')
        else:
            # 在指定代码前插入 dbg()
            code = 'dbg(); ' + ' '.join(args[1:])
            run_lua_code(code, wait_log=False, safe_mode=False)
    else:
        # 直接发送原始命令
        raw_cmd = ' '.join(args)
        send_command(raw_cmd, wait_log=wait_log)

if __name__ == '__main__':
    main()
