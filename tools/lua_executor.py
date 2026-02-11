#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
强化版 Lua 执行器 - 自动检测错误的智能包装

核心流程：
    1. 记录日志/异常当前位置
    2. 发送 Lua 代码
    3. 等待响应（确认游戏收到）
    4. 检查游戏日志新增 [error]
    5. 检查异常消息文件新增异常
    6. 综合判断：成功/失败/卡死

用法:
    from lua_executor import execute_lua, ExecuteResult

    result = execute_lua("print('test')")
    if result.success:
        print('成功')
    else:
        print(f'失败: {result.error}')
        if result.log_errors:
            print('日志错误:', result.log_errors)
"""

import os
import sys
import time
import json

# 添加 tools 目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from game_control import (
    run_lua_with_confirm,
    is_game_running,
    is_y3_helper_ready,
    wait_for_y3_helper_ready,
    send_y3helper
)

# 路径配置
LOG_DIR = os.path.join(SCRIPT_DIR, '..', '.log')
GAME_LOG = os.path.join(LOG_DIR, 'lua_player01.log')
MSG_FILE = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '/tmp')), 'y3helper_messages.jsonl')


class ExecuteResult:
    """执行结果封装"""
    def __init__(self):
        self.success = False           # 整体是否成功
        self.executed = False          # 游戏是否收到并执行
        self.alive = True              # 游戏是否存活（无心跳超时）
        self.log_errors = []           # 日志中的新错误
        self.exceptions = []           # 异常消息中的新异常
        self.error = None              # 主要错误信息
        self.warning = None            # 警告信息

    def __str__(self):
        status = '✓成功' if self.success else '✗失败'
        parts = [status]
        if self.error:
            parts.append(f'错误: {self.error}')
        if self.log_errors:
            parts.append(f'日志错误: {len(self.log_errors)}条')
        if self.exceptions:
            parts.append(f'异常: {len(self.exceptions)}条')
        if self.warning:
            parts.append(f'警告: {self.warning}')
        return ' | '.join(parts)


def get_log_line_count():
    """获取日志文件当前行数"""
    try:
        if not os.path.exists(GAME_LOG):
            return 0
        with open(GAME_LOG, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except:
        return 0


def get_msg_line_count():
    """获取消息文件当前行数"""
    try:
        if not os.path.exists(MSG_FILE):
            return 0
        with open(MSG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except:
        return 0


def get_new_log_errors(since_line):
    """获取日志中新增的 [error] 行"""
    errors = []
    try:
        if not os.path.exists(GAME_LOG):
            return []
        with open(GAME_LOG, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if i < since_line:
                continue
            if '[error]' in line.lower():
                errors.append(line.strip())
    except:
        pass
    return errors


def get_new_exceptions(since_line):
    """获取消息文件中新增的异常"""
    exceptions = []
    try:
        if not os.path.exists(MSG_FILE):
            return []
        with open(MSG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if i < since_line:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get('type') == 'exception':
                    exceptions.append(data.get('message', '未知异常'))
            except:
                pass
    except:
        pass
    return exceptions


def execute_lua(code, timeout=10, check_errors=True, auto_recover=True):
    """执行 Lua 代码并自动检查错误

    Args:
        code: Lua 代码字符串
        timeout: 响应超时时间（秒）
        check_errors: 是否检查日志错误（默认True）
        auto_recover: 如果游戏卡死，是否自动发送 continue（默认True）

    Returns:
        ExecuteResult: 执行结果对象
    """
    result = ExecuteResult()

    # 1. 检查游戏是否运行
    running, msg = is_game_running()
    if not running:
        result.success = False
        result.alive = False
        result.error = f'游戏未运行: {msg}'
        return result

    # 2. 检查游戏是否就绪
    if not is_y3_helper_ready():
        print('[等待] 游戏尚未初始化完成...')
        if not wait_for_y3_helper_ready(timeout=60):
            result.success = False
            result.error = '游戏初始化超时'
            return result

    # 3. 记录当前位置（执行前）
    log_line_before = get_log_line_count()
    msg_line_before = get_msg_line_count()

    # 4. 发送 Lua 代码
    print(f'[执行] {code[:80]}{"..." if len(code) > 80 else ""}')
    response = run_lua_with_confirm(code, timeout=timeout)

    # 5. 检查响应
    result.executed = response['executed']

    if not response['executed']:
        # 游戏没有响应（可能卡死）
        result.success = False
        result.alive = False
        result.error = response.get('error', '游戏无响应')

        # 尝试自动恢复
        if auto_recover:
            print('[恢复] 尝试发送 continue 命令...')
            send_y3helper('workbench.action.debug.continue')
            time.sleep(2)

            # 再次检查心跳
            heartbeat_response = run_lua_with_confirm("print('[HEARTBEAT_CHECK]')", timeout=5)
            if heartbeat_response['executed']:
                result.alive = True
                result.warning = '游戏已从冻结中恢复'
                print('[恢复] 游戏已恢复')
            else:
                result.warning = '游戏仍无响应，可能需要重启'
                print('[恢复] 游戏仍无响应')

        # 即使无响应，也检查错误
        if check_errors:
            time.sleep(0.5)  # 给日志一点写入时间
            result.log_errors = get_new_log_errors(log_line_before)
            result.exceptions = get_new_exceptions(msg_line_before)

        return result

    # 6. 游戏有响应，检查错误（关键！）
    if check_errors:
        # 给日志文件一点时间刷新（重要！）
        time.sleep(0.3)

        result.log_errors = get_new_log_errors(log_line_before)
        result.exceptions = get_new_exceptions(msg_line_before)

    # 7. 综合判断
    if result.log_errors or result.exceptions:
        # 有错误 = 失败
        result.success = False
        error_parts = []
        if result.exceptions:
            error_parts.append(f'{len(result.exceptions)}个异常')
        if result.log_errors:
            error_parts.append(f'{len(result.log_errors)}个日志错误')
        result.error = '执行中发现: ' + ', '.join(error_parts)
    else:
        # 无错误 = 成功
        result.success = True

    return result


def execute_lua_file(filename, timeout=10, check_errors=True, auto_recover=True):
    """执行 tools/ 目录下的 Lua 文件

    Args:
        filename: 文件名（不含 .lua 后缀）
        其他参数同 execute_lua

    Returns:
        ExecuteResult
    """
    lua_path = f"tools.{filename}"
    if lua_path.endswith('.lua'):
        lua_path = lua_path[:-4]

    code = f"_reloadlua('{lua_path}')"
    return execute_lua(code, timeout=timeout, check_errors=check_errors, auto_recover=auto_recover)


def print_result(result, verbose=True):
    """打印执行结果

    Args:
        result: ExecuteResult 对象
        verbose: 是否显示详细错误信息
    """
    if result.success:
        print(f'[成功] ✓ 命令执行完成')
    else:
        print(f'[失败] ✗ {result.error}')

    if result.warning:
        print(f'[警告] ⚠ {result.warning}')

    if verbose:
        if result.exceptions:
            print(f'\n[异常] 发现 {len(result.exceptions)} 个引擎异常:')
            for exc in result.exceptions[:5]:  # 最多显示5个
                print(f'  • {exc}')
            if len(result.exceptions) > 5:
                print(f'  ... 还有 {len(result.exceptions)-5} 个异常')

        if result.log_errors:
            print(f'\n[日志错误] 发现 {len(result.log_errors)} 个错误:')
            for err in result.log_errors[:5]:
                print(f'  • {err}')
            if len(result.log_errors) > 5:
                print(f'  ... 还有 {len(result.log_errors)-5} 个错误')


def main():
    """命令行接口"""
    if len(sys.argv) < 2:
        print(__doc__)
        print('\n用法:')
        print('  python lua_executor.py "Lua代码"')
        print('  python lua_executor.py --file 脚本名')
        print('\n示例:')
        print('  python lua_executor.py "print(\'test\')"')
        print('  python lua_executor.py --file pet_test')
        return

    if sys.argv[1] == '--file':
        if len(sys.argv) < 3:
            print('[错误] 请指定文件名')
            return
        result = execute_lua_file(sys.argv[2])
    else:
        code = ' '.join(sys.argv[1:])
        result = execute_lua(code)

    print_result(result)
    sys.exit(0 if result.success else 1)


if __name__ == '__main__':
    main()
