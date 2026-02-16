#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PostToolUse Hook: Auto-check game log errors after Bash execution.

Trigger: Bash command contains game_control or lua_executor
Checks:
  1. Log file for .lua: errors and [error] markers
  2. Bash output for [RUN success/fail] markers
  3. Bash exit code (non-zero = fail)

Output: JSON block decision if errors found
"""
import sys
import json
import os
import re
import time

def find_log_file():
    """Find game log file from hook script location."""
    hook_dir = os.path.dirname(os.path.abspath(__file__))
    # .claude/hooks/ -> script/
    script_dir = os.path.dirname(os.path.dirname(hook_dir))
    log_path = os.path.join(script_dir, '.log', 'lua_player01.log')
    if os.path.exists(log_path):
        return log_path
    return None

def read_log_tail(log_path, lines=30):
    """Read last N lines of log file."""
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) >= lines else all_lines
    except Exception:
        return []

def check_log_errors(log_lines):
    """Check log lines for real Lua errors.

    Y3 engine log format:
      [time][debug][...path/file.lua:line]: print content   <-- normal print, NOT error
      [time][error][...]: error message                     <-- real error
      ...file.lua:123: attempt to call nil                  <-- raw Lua error (no [debug] tag)

    So: [debug] lines with .lua:line are NORMAL prints.
    Only [error] lines or raw .lua:line lines (without [debug]/[info]/[warn]) are real errors.
    """
    errors = []
    for line in log_lines:
        line = line.strip()
        if not line:
            continue
        # [error] tag = definite error
        if '[error]' in line.lower():
            errors.append(line)
        # Raw .lua:linenum WITHOUT [debug]/[info]/[warn] prefix = real Lua crash
        elif re.search(r'\.lua:\d+', line):
            # Skip if it has a normal log level tag (these are just print() outputs)
            if re.search(r'\[\s*(debug|info|warn)\s*\]', line, re.IGNORECASE):
                continue
            errors.append(line)
    return errors

def main():
    # Read stdin JSON from Claude Code
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    if tool_name != 'Bash':
        sys.exit(0)

    # Get the command that was executed
    tool_input = input_data.get('tool_input', {})
    command = tool_input.get('command', '')

    # Only trigger for commands that actually RUN game_control or lua_executor
    # Skip echo, grep, cat, etc that merely mention these names in arguments
    cmd_stripped = command.strip()
    # Handle "cd ... && python ..." or "cd ... ; python ..." chains
    # Take the last command in a chain
    for sep in ['&&', ';', '|']:
        if sep in cmd_stripped:
            cmd_stripped = cmd_stripped.split(sep)[-1].strip()
    # Must actually start with python (the real execution)
    if not cmd_stripped.startswith('python'):
        sys.exit(0)
    # Must contain game_control or lua_executor as the script being run
    if 'game_control' not in cmd_stripped and 'lua_executor' not in cmd_stripped:
        sys.exit(0)

    # Skip non-test commands (status, kill, launch, etc)
    skip_cmds = ['status', 'kill', 'launch', 'screenshot', 'ss', 'continue', 'c ', 'pause', 'p ',
                 'enter', 'restart', 'frestart']
    for skip in skip_cmds:
        if f' {skip}' in command or command.endswith(f' {skip}'):
            sys.exit(0)

    # Get Bash output
    tool_response = input_data.get('tool_response', '')
    if isinstance(tool_response, dict):
        bash_output = tool_response.get('stdout', '') + tool_response.get('stderr', '')
    else:
        bash_output = str(tool_response)

    error_reasons = []

    # Check 1: Explicit failure markers in output (ASCII only, no encoding issues)
    fail_markers = ['[RUN-FAIL]', '[RUN\u5931\u8d25]']
    success_markers = ['[RUN-OK]', '[RUN\u6210\u529f]']

    has_failure = any(m in bash_output for m in fail_markers)
    has_success = any(m in bash_output for m in success_markers)

    if has_failure:
        for line in bash_output.split('\n'):
            if any(m in line for m in fail_markers) or '[error' in line.lower():
                error_reasons.append(line.strip())

    # Check 2: run/lua command with no success/fail marker = game stuck
    is_run_cmd = 'game_control' in command and (' run ' in command or ' lua ' in command)
    if is_run_cmd and not has_success and not has_failure:
        error_reasons.append(
            'GAME STUCK: No [RUN-OK] or [RUN-FAIL] in output. '
            'Run: python game_control.py frestart'
        )

    # Check 3: Check game log for .lua: errors (only recent lines)
    log_path = find_log_file()
    if log_path and is_run_cmd:
        log_lines = read_log_tail(log_path, lines=15)
        log_errors = check_log_errors(log_lines)
        if log_errors:
            recent = log_errors[-5:]
            error_reasons.append(
                'LUA ERRORS in log (last 15 lines):\n' + '\n'.join(recent)
            )

    # Check 4: Heartbeat verification (most important check!)
    # game_control.py now does heartbeat verification internally,
    # so [RUN-FAIL] already means heartbeat failed.
    # But as a safety net, also check if output mentions heartbeat issues
    heartbeat_warnings = ['心跳中断', '心跳已异常', '游戏冻结', '恢复失败', 'frestart']
    if any(w in bash_output for w in heartbeat_warnings) and not has_success:
        if not error_reasons:  # Don't duplicate if already captured
            error_reasons.append(
                'HEARTBEAT ISSUE detected in output. Game may be frozen.'
            )

    # Block if errors found
    if error_reasons:
        output = {
            "decision": "block",
            "reason": "GAME TEST ERROR - must fix before continuing:\n" + '\n'.join(error_reasons)
        }
        # Use ensure_ascii=True to avoid encoding issues on Windows
        print(json.dumps(output, ensure_ascii=True))
        sys.exit(0)

    # No errors, pass through
    sys.exit(0)

if __name__ == '__main__':
    main()
