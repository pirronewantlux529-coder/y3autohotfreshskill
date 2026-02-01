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

# Y3 Helper 就绪标记
Y3_HELPER_READY_MARK = '[Y3_HELPER_READY]'

def is_y3_helper_ready():
    """检查游戏是否已完成初始化（日志中有就绪标记）"""
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            return Y3_HELPER_READY_MARK in content
    except:
        return False

def wait_for_y3_helper_ready(timeout=60):
    """等待游戏完成初始化

    Args:
        timeout: 超时时间（秒）

    Returns:
        bool: 是否就绪
    """
    print(f'[等待] 等待游戏初始化完成...')
    start = time.time()
    while time.time() - start < timeout:
        if is_y3_helper_ready():
            print(f'[就绪] 游戏已初始化完成')
            return True
        time.sleep(0.5)
    print(f'[超时] 等待游戏初始化超时（{timeout}秒）')
    return False

# 导入配置模块（自动检测路径）
try:
    from config import get_config, get_game_args
    _CONFIG = None

    def _get_cached_config():
        global _CONFIG
        if _CONFIG is None:
            _CONFIG = get_config()
        return _CONFIG
except ImportError:
    # 配置模块不存在时的后备方案
    _CONFIG = None
    def _get_cached_config():
        return {
            'game_exe': None,
            'project_path': None,
            'level_id': None,
            'errors': ['config.py 模块不存在'],
        }
    def get_game_args(config, debug=False):
        return []

def reload(module='base.hotfresh'):
    """热更新模块（通过Y3 Helper）"""
    return run_lua_with_confirm(f"_reloadlua('{module}')")

def run_lua_file(filename, wait_log=True, skip_ready_check=False):
    """执行tools目录下的lua脚本（通过Y3 Helper热更新）

    Args:
        filename: 脚本名（不含.lua后缀）
        wait_log: 是否等待日志更新确认执行
        skip_ready_check: 是否跳过就绪检查
    """
    # 构造模块路径（不带.lua后缀）
    lua_path = f"tools.{filename}"
    if lua_path.endswith('.lua'):
        lua_path = lua_path[:-4]
    # 通过 Y3 Helper 执行热更新
    return run_lua_with_confirm(f"_reloadlua('{lua_path}')", skip_ready_check=skip_ready_check)

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

    # 通过 Y3 Helper 热更新执行
    lua_path = f'tools.temp.{temp_name}'
    return run_lua_with_confirm(f"_reloadlua('{lua_path}')")


def run_lua_with_confirm(code, timeout=10, skip_ready_check=False):
    """执行 Lua 代码并等待确认（需要 runlua_confirm 补丁）

    Args:
        code: Lua 代码
        timeout: 超时时间（秒）
        skip_ready_check: 是否跳过就绪检查（用于 restart 等特殊命令）

    Returns:
        dict: {
            'success': bool,      # 是否成功
            'executed': bool,     # 游戏是否真正执行了
            'result': any,        # 执行结果
            'error': str          # 错误信息
        }
    """
    result = {
        'success': False,
        'executed': False,
        'result': None,
        'error': None
    }

    # 检查游戏是否运行
    running, msg = is_game_running()
    if not running:
        result['error'] = f'游戏未运行: {msg}'
        return result

    # 检查游戏是否已完成初始化（除非跳过检查）
    if not skip_ready_check and not is_y3_helper_ready():
        print('[等待] 游戏尚未初始化完成，等待中...')
        if not wait_for_y3_helper_ready(timeout=60):
            result['error'] = '游戏初始化超时，请检查游戏状态'
            return result

    # 发送命令并等待响应
    response = send_y3helper('y3-helper.runLua', [code], wait_response=True, timeout=timeout)

    if response is None:
        result['error'] = '未收到响应（可能游戏卡死或未打补丁）'
        return result

    if isinstance(response, dict):
        # 检查响应结构
        if 'result' in response:
            # 标准 JSON-RPC 结果格式
            results = response.get('result', [])
            if results and len(results) > 0:
                first = results[0]
                result['executed'] = True
                result['success'] = first.get('success', False)
                result['result'] = first.get('result')
                if not result['success']:
                    result['error'] = first.get('error', '未知错误')
            else:
                result['error'] = '响应结果为空'
        elif 'method' in response:
            # 游戏端回显消息格式：{'method': 'command', 'params': {...}}
            # 收到这个说明游戏端处理了命令（即使没有返回结果）
            result['executed'] = True
            result['success'] = True
            result['result'] = response.get('params', {}).get('data', '')
        elif 'error' in response:
            result['error'] = response['error']
        else:
            result['error'] = f'未知响应格式: {response}'
    else:
        result['error'] = f'响应类型错误: {type(response)}'

    return result


def restart():
    """重启游戏（通过热更新restart_game.lua）"""
    # restart 跳过 ready 检查，因为重启后会重新加载 debugs.lua
    return run_lua_file('restart_game', skip_ready_check=True)

def quick_enter():
    """快速进入游戏"""
    return run_lua_file('quick_enter')

def pet_test():
    """打开宠物测试界面"""
    return run_lua_file('pet_test')

def goto_training():
    """传送到演武场（战斗测试区域）"""
    return run_lua_file('goto_training')

def start_game(debug=False):
    """启动游戏客户端（使用自动检测的配置）"""
    config = _get_cached_config()

    if config.get('errors'):
        print('[错误] 配置检测失败:')
        for err in config['errors']:
            print(f'  - {err}')
        return False

    game_exe = config.get('game_exe')
    if not game_exe or not os.path.exists(game_exe):
        print(f'[错误] 游戏可执行文件不存在: {game_exe}')
        print('[提示] 请确保 .vscode/settings.json 中有正确的 Y3-Helper.EditorPath')
        return False

    game_args = get_game_args(config, debug=debug)

    try:
        cmd = [game_exe] + game_args
        print(f'[启动] 正在启动游戏...')
        print(f'[配置] 项目: {config.get("project_path")}')
        print(f'[配置] 关卡ID: {config.get("level_id")}')

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

def send_y3helper(command, args=None, wait_response=False, timeout=10):
    """发送命令到 Y3 Helper

    Args:
        command: 命令名称
        args: 命令参数
        wait_response: 是否等待响应（需要打过 runlua_confirm 补丁）
        timeout: 超时时间（秒）

    Returns:
        bool 或 dict: 如果 wait_response=False 返回 bool
                      如果 wait_response=True 返回响应字典或 None
    """
    port = read_helper_port()
    if not port:
        print('[错误] 找不到 Y3 Helper 端口，请确认 Cursor/VSCode 已打开项目')
        return False if not wait_response else None

    try:
        sock = socket.socket()
        sock.settimeout(timeout)
        sock.connect(('127.0.0.1', port))

        msg = {
            'method': 'command',
            'id': 1,
            'params': {'command': command, 'args': args or []}
        }
        data = json.dumps(msg).encode('utf-8')
        sock.send(struct.pack('>I', len(data)) + data)

        if not wait_response:
            # 给游戏一点时间处理命令
            time.sleep(0.3)
            sock.close()
            return True

        # 等待响应
        try:
            # 读取长度头（4字节）
            header = b''
            while len(header) < 4:
                chunk = sock.recv(4 - len(header))
                if not chunk:
                    break
                header += chunk

            if len(header) < 4:
                print('[警告] 未收到完整响应头')
                sock.close()
                return None

            length = struct.unpack('>I', header)[0]

            # 读取响应体
            body = b''
            while len(body) < length:
                chunk = sock.recv(min(4096, length - len(body)))
                if not chunk:
                    break
                body += chunk

            sock.close()

            if len(body) < length:
                print('[警告] 响应数据不完整')
                return None

            response = json.loads(body.decode('utf-8'))
            return response

        except socket.timeout:
            print('[超时] 等待 Y3 Helper 响应超时')
            sock.close()
            return None

    except ConnectionRefusedError:
        print('[错误] Y3 Helper 连接被拒绝，请确认 Cursor/VSCode 已打开项目')
        return False if not wait_response else None
    except Exception as e:
        print(f'[错误] {e}')
        return False if not wait_response else None

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
    """启动游戏（自动选择最佳方式）

    尝试顺序：
    1. 计划任务（无UAC弹窗）
    2. 直接启动（需要UAC确认）
    """
    # 1. 尝试计划任务方式（无UAC）
    try:
        result = subprocess.run(
            ['schtasks', '/run', '/tn', 'Y3LaunchGame'],
            capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            print('[OK] 游戏启动命令已发送（通过计划任务，无UAC弹窗）')
            return True
        else:
            print('[提示] 计划任务未配置，尝试直接启动...')
    except Exception as e:
        print(f'[提示] 计划任务检测失败: {e}，尝试直接启动...')

    # 2. 回退到直接启动方式
    print('[提示] 如需无UAC启动，请以管理员身份运行 setup_launch_task.bat')
    return launch_game_direct()

def launch_game_y3helper():
    """通过 Y3 Helper 启动游戏（备用方式，会弹UAC）"""
    if send_y3helper('y3-helper.launchGame'):
        print('[OK] 游戏启动命令已发送（通过Y3 Helper）')
        return True
    return False


def launch_game_direct():
    """直接启动游戏（会弹UAC，但不依赖Y3 Helper）

    使用自动检测的配置直接运行游戏可执行文件。
    适用于 Y3 Helper 不可用的情况。
    """
    from config import get_config, get_game_args

    config = get_config()
    if config['errors']:
        print('[错误] 配置检测失败:')
        for err in config['errors']:
            print(f'  - {err}')
        return False

    game_exe = config.get('game_exe')
    if not game_exe or not os.path.exists(game_exe):
        print(f'[错误] 找不到游戏可执行文件: {game_exe}')
        return False

    args = get_game_args(config, debug=True)
    if not args:
        print('[错误] 无法生成启动参数')
        return False

    game_dir = os.path.dirname(game_exe)

    print('[启动游戏] 配置信息:')
    print(f'  游戏路径: {game_exe}')
    print(f'  项目路径: {config.get("project_path")}')
    print(f'  关卡 ID: {config.get("level_id")}')

    try:
        # 使用 subprocess.Popen 启动游戏（非阻塞）
        subprocess.Popen(
            [game_exe] + args,
            cwd=game_dir,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        print('[OK] 游戏启动命令已发送（直接启动，可能需要UAC确认）')
        return True
    except Exception as e:
        print(f'[错误] 启动失败: {e}')
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


def show_config():
    """显示自动检测的配置"""
    try:
        from config import print_config
        print_config()
    except ImportError:
        print('[错误] config.py 模块不存在')

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print('\n快捷命令:')
        print('  config           - 显示自动检测的配置（路径、关卡ID等）')
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
        print('  luac "代码"      - 执行 Lua 并等待确认（需要 runlua_confirm 补丁）')
        print('\n选项:')
        print('  --no-wait        - 不等待日志更新确认')
        return

    # 检查是否有 --no-wait 选项
    wait_log = '--no-wait' not in sys.argv
    args = [a for a in sys.argv[1:] if a != '--no-wait']

    cmd = args[0].lower() if args else ''

    if cmd == 'config':
        show_config()
    elif cmd == 'status':
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
    elif cmd == 'lua' or cmd == 'luac' or cmd == 'lua-confirm':
        # lua 命令默认带确认（需要 runlua_confirm 补丁）
        # args[0] 是 'lua'，args[1:] 是代码
        if len(args) < 2:
            print('[错误] 请指定要执行的 Lua 代码')
            return
        code = ' '.join(args[1:])
        print(f'[发送] {code[:50]}...' if len(code) > 50 else f'[发送] {code}')
        result = run_lua_with_confirm(code)
        if result['success']:
            print(f'[成功] 游戏已执行命令')
            if result['result']:
                print(f'[返回] {result["result"]}')
        else:
            print(f'[失败] {result["error"]}')
            if not result['executed']:
                print('[提示] 游戏可能卡死，尝试: python game_control.py kill')
    elif cmd == 'lua-nc' or cmd == 'lua-noconfirm':
        # 无确认的 Lua 执行（旧模式，不等待响应）
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
        # 未知命令，尝试作为 lua 代码执行
        raw_cmd = ' '.join(args)
        print(f'[未知命令] 尝试作为 Lua 代码执行: {raw_cmd}')
        run_lua_with_confirm(raw_cmd)

if __name__ == '__main__':
    main()
