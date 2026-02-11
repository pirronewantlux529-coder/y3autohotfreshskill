#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
心跳监控器 - 通过定期发送 Lua 命令检测游戏是否卡死

原理：
    游戏卡在调试器断点时，所有 Lua 命令都不会响应。
    通过发送心跳命令并检测超时，可以可靠地检测游戏冻结。
    检测到冻结后，自动发送 continue 命令恢复，并记录错误信息。

用法:
    python heartbeat_monitor.py              # 默认每10秒心跳，5秒超时
    python heartbeat_monitor.py --interval 5 # 每5秒心跳
    python heartbeat_monitor.py --once       # 只检测一次（用于外部脚本调用）
"""

import socket
import struct
import json
import os
import sys
import time
import re
import argparse
from datetime import datetime

# ===== 配置 =====
HEARTBEAT_INTERVAL = 10   # 心跳间隔（秒）
HEARTBEAT_TIMEOUT = 5     # 心跳超时（秒），超时 = 游戏可能冻结
MAX_CONTINUE_RETRIES = 3  # 连续 continue 失败后放弃
COOLDOWN_AFTER_RECOVER = 5  # 恢复后冷却时间（秒）

# ===== 路径 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, '..', '.log')
GAME_LOG = os.path.join(LOG_DIR, 'lua_player01.log')
MONITOR_LOG = os.path.join(LOG_DIR, 'monitor_errors.log')
MSG_FILE = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '/tmp')), 'y3helper_messages.jsonl')
PORT_FILE = os.path.join(SCRIPT_DIR, '..', 'log', 'helper_port.lua')

# ===== 统计 =====
stats = {
    'heartbeats_sent': 0,
    'heartbeats_ok': 0,
    'freezes_detected': 0,
    'recoveries': 0,
    'errors_found': 0,
    'start_time': None,
}


def log(msg, level='INFO'):
    """输出日志到控制台和日志文件"""
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'[{ts}][{level}] {msg}'
    print(line)
    try:
        os.makedirs(os.path.dirname(MONITOR_LOG), exist_ok=True)
        with open(MONITOR_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass


def read_helper_port():
    """读取 Y3 Helper 端口"""
    try:
        with open(PORT_FILE, 'r') as f:
            match = re.search(r'return\s*(\d+)', f.read())
            if match:
                return int(match.group(1))
    except:
        pass
    return None


def send_command(command, args=None, timeout=5):
    """发送命令到 Y3 Helper 并等待响应

    Returns:
        dict 或 None: 响应字典，超时或错误返回 None
    """
    port = read_helper_port()
    if not port:
        return None

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

        # 读取响应头（4字节长度）
        header = b''
        while len(header) < 4:
            chunk = sock.recv(4 - len(header))
            if not chunk:
                break
            header += chunk

        if len(header) < 4:
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
            return None

        return json.loads(body.decode('utf-8'))

    except socket.timeout:
        try:
            sock.close()
        except:
            pass
        return None
    except ConnectionRefusedError:
        return None
    except Exception:
        return None


def send_heartbeat(timeout=None):
    """发送心跳命令

    Returns:
        bool: True = 游戏正常响应, False = 超时/冻结
    """
    if timeout is None:
        timeout = HEARTBEAT_TIMEOUT

    ts = int(time.time())
    code = f"print('[HEARTBEAT] {ts}')"
    response = send_command('y3-helper.runLua', [code], timeout=timeout)

    if response is None:
        return False

    # 检查响应是否表示成功执行
    if isinstance(response, dict):
        if 'result' in response:
            results = response.get('result', [])
            if results and len(results) > 0:
                return results[0].get('success', False)
        elif 'method' in response:
            # 命令回显格式，说明游戏处理了
            return True
    return False


def send_continue():
    """发送 continue 命令恢复游戏

    Returns:
        bool: True = 命令发送成功
    """
    # continue 不需要等待 Lua 响应，只需要 Y3 Helper 收到命令
    try:
        port = read_helper_port()
        if not port:
            return False

        sock = socket.socket()
        sock.settimeout(3)
        sock.connect(('127.0.0.1', port))

        msg = {
            'method': 'command',
            'id': 1,
            'params': {'command': 'workbench.action.debug.continue', 'args': []}
        }
        data = json.dumps(msg).encode('utf-8')
        sock.send(struct.pack('>I', len(data)) + data)
        time.sleep(0.3)
        sock.close()
        return True
    except:
        return False


def get_recent_exceptions(since_line=0):
    """从 y3helper_messages.jsonl 获取最近的异常

    Args:
        since_line: 从第几行开始读取（跳过已处理的）

    Returns:
        tuple: (异常列表, 当前总行数)
    """
    exceptions = []
    total_lines = 0
    try:
        if not os.path.exists(MSG_FILE):
            return [], 0
        with open(MSG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        total_lines = len(lines)
        for i, line in enumerate(lines):
            if i < since_line:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get('type') == 'exception':
                    exceptions.append(data)
            except:
                pass
    except:
        pass
    return exceptions, total_lines


def get_recent_errors(since_line=0):
    """从游戏日志获取最近的 [error] 行

    Args:
        since_line: 从第几行开始读取

    Returns:
        tuple: (错误列表, 当前总行数)
    """
    errors = []
    total_lines = 0
    try:
        if not os.path.exists(GAME_LOG):
            return [], 0
        with open(GAME_LOG, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        total_lines = len(lines)
        for i, line in enumerate(lines):
            if i < since_line:
                continue
            if '[error]' in line:
                errors.append(line.strip())
    except:
        pass
    return errors, total_lines


def attempt_recovery():
    """尝试从冻结中恢复

    Returns:
        bool: True = 恢复成功
    """
    log('>>> 检测到游戏冻结！尝试恢复...', 'WARN')
    stats['freezes_detected'] += 1

    for attempt in range(1, MAX_CONTINUE_RETRIES + 1):
        log(f'    发送 continue ({attempt}/{MAX_CONTINUE_RETRIES})...', 'WARN')
        send_continue()
        time.sleep(2)  # 等待游戏恢复

        # 验证是否恢复
        if send_heartbeat(timeout=HEARTBEAT_TIMEOUT):
            log('<<< 游戏已恢复！', 'INFO')
            stats['recoveries'] += 1
            return True

        log(f'    第{attempt}次 continue 后仍无响应', 'WARN')

    log('!!! 多次 continue 后仍无法恢复，游戏可能需要重启', 'ERROR')
    return False


def check_result(msg_line_before, log_line_before):
    """在恢复后检查错误信息"""
    # 检查新异常
    exceptions, msg_line_now = get_recent_exceptions(msg_line_before)
    if exceptions:
        log(f'=== 发现 {len(exceptions)} 个异常 ===', 'ERROR')
        for exc in exceptions:
            msg = exc.get('message', '未知异常')
            log(f'  [EXCEPTION] {msg}', 'ERROR')
        stats['errors_found'] += len(exceptions)

    # 检查新日志错误
    errors, log_line_now = get_recent_errors(log_line_before)
    if errors:
        log(f'=== 发现 {len(errors)} 个日志错误 ===', 'ERROR')
        for err in errors[-5:]:  # 最多显示5条
            log(f'  [LOG_ERROR] {err}', 'ERROR')
        stats['errors_found'] += len(errors)

    return msg_line_now, log_line_now


def run_once():
    """执行一次心跳检测

    Returns:
        dict: {
            'alive': bool,       # 游戏是否存活
            'recovered': bool,   # 是否经历了恢复
            'errors': list       # 发现的错误
        }
    """
    result = {'alive': False, 'recovered': False, 'errors': []}

    # 记录当前位置
    _, msg_line = get_recent_exceptions()
    _, log_line = get_recent_errors()

    # 发送心跳
    if send_heartbeat():
        result['alive'] = True
        # 即使游戏存活，也检查新错误
        errors, _ = get_recent_errors(log_line)
        result['errors'] = errors
        return result

    # 游戏冻结，尝试恢复
    if attempt_recovery():
        result['alive'] = True
        result['recovered'] = True
    else:
        result['alive'] = False

    # 检查错误
    exceptions, _ = get_recent_exceptions(msg_line)
    for exc in exceptions:
        result['errors'].append(f"[EXCEPTION] {exc.get('message', '')}")

    errors, _ = get_recent_errors(log_line)
    result['errors'].extend(errors)

    return result


def run_loop(interval=None):
    """持续心跳监控循环"""
    if interval is None:
        interval = HEARTBEAT_INTERVAL

    stats['start_time'] = time.time()

    log('=' * 60)
    log(f'心跳监控器启动 (间隔={interval}s, 超时={HEARTBEAT_TIMEOUT}s)')
    log(f'游戏日志: {GAME_LOG}')
    log(f'消息文件: {MSG_FILE}')
    log(f'监控日志: {MONITOR_LOG}')
    log('=' * 60)

    # 初始化行数跟踪
    _, msg_line = get_recent_exceptions()
    _, log_line = get_recent_errors()

    consecutive_failures = 0

    try:
        while True:
            stats['heartbeats_sent'] += 1

            # 发送心跳
            alive = send_heartbeat()

            if alive:
                stats['heartbeats_ok'] += 1
                consecutive_failures = 0

                # 检查新错误（即使游戏正常运行也要监控）
                new_errors, new_log_line = get_recent_errors(log_line)
                if new_errors:
                    log(f'--- 检测到 {len(new_errors)} 个新的日志错误 ---', 'WARN')
                    for err in new_errors[-3:]:
                        log(f'  {err}', 'ERROR')
                    stats['errors_found'] += len(new_errors)
                log_line = new_log_line

                # 检查新异常
                new_exceptions, new_msg_line = get_recent_exceptions(msg_line)
                if new_exceptions:
                    log(f'--- 检测到 {len(new_exceptions)} 个新异常 ---', 'WARN')
                    for exc in new_exceptions:
                        log(f'  [EXC] {exc.get("message", "")}', 'ERROR')
                    stats['errors_found'] += len(new_exceptions)
                msg_line = new_msg_line

            else:
                consecutive_failures += 1
                log(f'心跳超时 (连续失败: {consecutive_failures})', 'WARN')

                # 记录恢复前的位置
                pre_msg = msg_line
                pre_log = log_line

                # 尝试恢复
                if attempt_recovery():
                    consecutive_failures = 0
                    # 恢复后检查错误
                    msg_line, log_line = check_result(pre_msg, pre_log)
                    # 恢复后冷却
                    time.sleep(COOLDOWN_AFTER_RECOVER)
                    continue
                else:
                    if consecutive_failures >= 5:
                        log('连续5次无法恢复，退出监控', 'ERROR')
                        break

            time.sleep(interval)

    except KeyboardInterrupt:
        log('\n监控器被手动停止')
    finally:
        # 打印统计
        elapsed = time.time() - stats['start_time'] if stats['start_time'] else 0
        log('=' * 60)
        log(f'监控器统计:')
        log(f'  运行时长: {elapsed:.0f}s')
        log(f'  心跳发送: {stats["heartbeats_sent"]}')
        log(f'  心跳成功: {stats["heartbeats_ok"]}')
        log(f'  冻结检测: {stats["freezes_detected"]}')
        log(f'  成功恢复: {stats["recoveries"]}')
        log(f'  错误发现: {stats["errors_found"]}')
        log('=' * 60)


def set_heartbeat_timeout(value):
    global HEARTBEAT_TIMEOUT
    HEARTBEAT_TIMEOUT = value


def main():
    parser = argparse.ArgumentParser(description='Y3 游戏心跳监控器')
    parser.add_argument('--interval', type=int, default=HEARTBEAT_INTERVAL,
                       help=f'心跳间隔秒数 (默认 {HEARTBEAT_INTERVAL})')
    parser.add_argument('--timeout', type=int, default=HEARTBEAT_TIMEOUT,
                       help=f'心跳超时秒数 (默认 {HEARTBEAT_TIMEOUT})')
    parser.add_argument('--once', action='store_true',
                       help='只检测一次（用于外部脚本调用）')
    args = parser.parse_args()

    set_heartbeat_timeout(args.timeout)

    if args.once:
        # 单次模式：检测一次并输出 JSON 结果
        result = run_once()
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if result['alive'] else 1)
    else:
        run_loop(interval=args.interval)


if __name__ == '__main__':
    main()
