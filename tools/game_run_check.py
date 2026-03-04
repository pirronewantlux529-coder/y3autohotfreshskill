#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import re
import time

RUN_SUCCESS_ANNOTATION = '-- @run-success:'
RUN_TIMEOUT_ANNOTATION = '-- @run-timeout:'
RUNTIME_ERROR_RE = re.compile(r'\.lua:\d+:\s')


def _next_command_id(run_id_file):
    last_id = 0
    try:
        if os.path.exists(run_id_file):
            with open(run_id_file, 'r', encoding='utf-8', errors='ignore') as f:
                last_id = int((f.read() or '0').strip() or '0')
    except Exception:
        last_id = 0

    cmd_id = last_id + 1
    try:
        with open(run_id_file, 'w', encoding='utf-8') as f:
            f.write(str(cmd_id))
    except Exception:
        pass
    return cmd_id


def _resolve_script_module_and_file(script_dir, filename):
    raw = (filename or '').strip().replace('\\', '/')
    if raw.endswith('.lua'):
        raw = raw[:-4]
    if raw.startswith('./'):
        raw = raw[2:]
    if raw.startswith('tools/'):
        raw = raw[6:]
    if raw.startswith('tools.'):
        raw = raw[6:]

    module_suffix = raw.replace('/', '.')
    module_name = f'tools.{module_suffix}'
    path_candidates = [
        os.path.join(script_dir, raw + '.lua'),
        os.path.join(script_dir, module_suffix.replace('.', os.sep) + '.lua'),
    ]
    script_path = path_candidates[0]
    for path in path_candidates:
        if os.path.exists(path):
            script_path = path
            break
    return module_name, script_path


def _read_run_annotations(script_path):
    marker = None
    timeout = None
    if not os.path.exists(script_path):
        return marker, timeout
    try:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[:120]
    except Exception:
        return marker, timeout

    for raw in lines:
        line = raw.strip()
        if line.startswith(RUN_SUCCESS_ANNOTATION):
            value = line[len(RUN_SUCCESS_ANNOTATION):].strip()
            if value:
                marker = value
        elif line.startswith(RUN_TIMEOUT_ANNOTATION):
            value = line[len(RUN_TIMEOUT_ANNOTATION):].strip()
            if value.isdigit():
                timeout = max(1, int(value))
    return marker, timeout


def _get_file_size(path):
    try:
        return os.path.getsize(path)
    except Exception:
        return 0


def _read_file_delta(path, offset):
    try:
        if not os.path.exists(path):
            return 0, ''
        size = os.path.getsize(path)
        if offset > size:
            offset = 0
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(offset)
            text = f.read()
            return f.tell(), text
    except Exception:
        return offset, ''


def _read_new_helper_exceptions(msg_file, offset):
    new_offset, text = _read_file_delta(msg_file, offset)
    exceptions = []
    if not text:
        return new_offset, exceptions

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except Exception:
            continue
        if data.get('type') == 'exception':
            exceptions.append(str(data.get('message') or '未知异常'))
    return new_offset, exceptions


def _extract_runtime_errors(lines):
    errors = []
    for line in lines:
        lower = line.lower()
        if '[error]' in lower:
            errors.append(line)
            continue
        if RUNTIME_ERROR_RE.search(line):
            errors.append(line)
    return errors


def _recover_by_continue(send_y3helper, rounds=3, sleep_seconds=1):
    for _ in range(rounds):
        send_y3helper('workbench.action.debug.continue')
        time.sleep(sleep_seconds)


def _wait_for_run_signals(log_file, msg_file, start_log_pos, start_msg_pos, *, success_markers, fail_marker, timeout):
    log_pos = start_log_pos
    msg_pos = start_msg_pos
    deadline = time.time() + timeout
    matched = set()
    saw_heartbeat = False
    errors = []
    exceptions = []

    while time.time() < deadline:
        log_pos, delta_log = _read_file_delta(log_file, log_pos)
        if delta_log:
            lines = [line.strip() for line in delta_log.splitlines() if line.strip()]
            for line in lines:
                if '[HEARTBEAT]' in line:
                    saw_heartbeat = True
                if fail_marker and fail_marker in line:
                    return {
                        'ok': False,
                        'reason': 'lua-fail-marker',
                        'matched': sorted(matched),
                        'missing': [m for m in success_markers if m not in matched],
                        'errors': errors,
                        'exceptions': exceptions,
                        'saw_heartbeat': saw_heartbeat,
                    }
                for marker in success_markers:
                    if marker and marker in line:
                        matched.add(marker)

            new_errors = _extract_runtime_errors(lines)
            if new_errors:
                errors.extend(new_errors[-20:])

        msg_pos, new_exceptions = _read_new_helper_exceptions(msg_file, msg_pos)
        if new_exceptions:
            exceptions.extend(new_exceptions[-20:])

        if len(matched) == len(success_markers):
            if errors:
                return {
                    'ok': False,
                    'reason': 'runtime-error',
                    'matched': sorted(matched),
                    'missing': [],
                    'errors': errors[-20:],
                    'exceptions': exceptions[-20:],
                    'saw_heartbeat': saw_heartbeat,
                }
            if exceptions:
                return {
                    'ok': False,
                    'reason': 'helper-exception',
                    'matched': sorted(matched),
                    'missing': [],
                    'errors': errors[-20:],
                    'exceptions': exceptions[-20:],
                    'saw_heartbeat': saw_heartbeat,
                }
            if saw_heartbeat:
                return {
                    'ok': True,
                    'reason': 'ok',
                    'matched': sorted(matched),
                    'missing': [],
                    'errors': [],
                    'exceptions': [],
                    'saw_heartbeat': True,
                }
        time.sleep(0.25)

    return {
        'ok': False,
        'reason': 'timeout',
        'matched': sorted(matched),
        'missing': [m for m in success_markers if m not in matched],
        'errors': errors[-20:],
        'exceptions': exceptions[-20:],
        'saw_heartbeat': saw_heartbeat,
    }


def _collect_recent_log_tail(log_file, lines=40):
    try:
        if not os.path.exists(log_file):
            return []
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            data = f.readlines()
        return [line.rstrip('\n') for line in data[-lines:]]
    except Exception:
        return []


def _run_with_markers(
    *,
    send_y3helper,
    is_game_running,
    log_file,
    msg_file,
    display_name,
    lua_code,
    cmd_id,
    success_marker,
    fail_marker,
    script_path=None,
    expect_marker=None,
    timeout=None,
):
    running, msg = is_game_running()
    if not running:
        print(f'[RUN-FAIL] {display_name} execution failed')
        print(f'[错误详情] 游戏未就绪: {msg}')
        return False

    declared_marker, declared_timeout = _read_run_annotations(script_path) if script_path else (None, None)
    final_expect = expect_marker or declared_marker
    final_timeout = timeout if timeout is not None else (declared_timeout or 10)

    required_markers = [success_marker]
    if final_expect:
        required_markers.append(final_expect)

    log_pos = _get_file_size(log_file)
    msg_pos = _get_file_size(msg_file)

    print(f'[RUN-ID] {cmd_id}')
    print(f'[RUN-CHECK] timeout={final_timeout}s markers={required_markers}')

    if not send_y3helper('y3-helper.runLua', [lua_code]):
        print(f'[RUN-FAIL] {display_name} execution failed')
        print('[错误详情] Y3 Helper 调用失败')
        return False

    send_y3helper('workbench.action.debug.continue')
    time.sleep(1)
    send_y3helper('workbench.action.debug.continue')

    result = _wait_for_run_signals(
        log_file,
        msg_file,
        log_pos,
        msg_pos,
        success_markers=required_markers,
        fail_marker=fail_marker,
        timeout=final_timeout,
    )

    if result['ok']:
        print(f'[RUN-OK] {display_name} executed successfully (cmd_id={cmd_id}, heartbeat verified)')
        return True

    _recover_by_continue(send_y3helper, rounds=3, sleep_seconds=1)
    print(f'[RUN-FAIL] {display_name} execution failed')
    print(f"[错误详情] 命令ID={cmd_id}, reason={result['reason']}")
    if result['missing']:
        print(f"[错误详情] 未命中标记: {' | '.join(result['missing'])}")
    if result['reason'] == 'timeout' and not result['saw_heartbeat']:
        print('[错误详情] 超时且未观察到心跳，已自动执行 continue 恢复')
    if result['errors']:
        print('[错误详情] 最近日志错误:')
        for line in result['errors'][-5:]:
            print(f'  {line}')
    if result['exceptions']:
        print('[错误详情] 最近 helper 异常:')
        for line in result['exceptions'][-5:]:
            print(f'  {line}')

    tail = _collect_recent_log_tail(log_file, lines=20)
    if tail:
        print('[错误详情] 日志尾部(20行):')
        for line in tail:
            print(f'  {line}')
    return False


def run_script_with_checks(
    *,
    send_y3helper,
    is_game_running,
    script_dir,
    log_file,
    msg_file,
    run_id_file,
    filename,
    expect_marker=None,
    timeout=None,
):
    lua_path, script_path = _resolve_script_module_and_file(script_dir, filename)
    cmd_id = _next_command_id(run_id_file)
    success_marker = f'[RUN-CMD-OK] id={cmd_id}'
    fail_marker = f'[RUN-CMD-FAIL] id={cmd_id}'
    lua_code = (
        'do '
        f'local __ok,__err=pcall(function() _reloadlua(\'{lua_path}\') end); '
        f'if __ok then print(\'{success_marker}\') '
        f'else print(\'{fail_marker} \'..tostring(__err)); error(__err) end '
        'end'
    )
    return _run_with_markers(
        send_y3helper=send_y3helper,
        is_game_running=is_game_running,
        log_file=log_file,
        msg_file=msg_file,
        display_name=f'script {filename}',
        lua_code=lua_code,
        cmd_id=cmd_id,
        success_marker=success_marker,
        fail_marker=fail_marker,
        script_path=script_path,
        expect_marker=expect_marker,
        timeout=timeout,
    )


def run_lua_with_checks(
    *,
    send_y3helper,
    is_game_running,
    log_file,
    msg_file,
    run_id_file,
    code,
    timeout=10,
):
    cmd_id = _next_command_id(run_id_file)
    success_marker = f'[RUN-CMD-OK] id={cmd_id}'
    fail_marker = f'[RUN-CMD-FAIL] id={cmd_id}'
    wrapped = (
        'do '
        f'local __ok,__err=pcall(function() {code} end); '
        f'if __ok then print(\'{success_marker}\') '
        f'else print(\'{fail_marker} \'..tostring(__err)); error(__err) end '
        'end'
    )
    return _run_with_markers(
        send_y3helper=send_y3helper,
        is_game_running=is_game_running,
        log_file=log_file,
        msg_file=msg_file,
        display_name='lua command',
        lua_code=wrapped,
        cmd_id=cmd_id,
        success_marker=success_marker,
        fail_marker=fail_marker,
        script_path=None,
        expect_marker=None,
        timeout=timeout,
    )
