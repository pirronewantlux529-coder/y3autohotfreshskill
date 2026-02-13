#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Game Watchdog - Background sentinel for Claude Code integration

Monitors game health in the background. When auto-recovery fails repeatedly,
exits with code 1 and a structured report that Claude automatically receives.

Usage:
    python game_watchdog.py                          # default: 3 max failures, 24h timeout
    python game_watchdog.py --max-failures 5         # exit after 5 consecutive recovery failures
    python game_watchdog.py --timeout 3600           # exit after 1 hour (seconds)
    python game_watchdog.py --check-interval 15      # check every 15 seconds

Claude Code integration (run_in_background=true):
    - While running: Claude is not disturbed
    - On exit(1): Claude receives the WATCHDOG ALERT with error details
    - On exit(0): Normal timeout/shutdown, no action needed
"""

import os
import sys
import time
import subprocess
import re
import argparse
from datetime import datetime

# === Paths ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, '..', '.log', 'lua_player01.log')
REPORT_FILE = os.path.join(SCRIPT_DIR, 'watchdog_report.log')

# === State ===
state = {
    'start_time': None,
    'last_log_mtime': 0,
    'last_log_size': 0,
    'last_error_count': 0,
    'consecutive_failures': 0,     # consecutive AUTO-RECOVERY failures
    'consecutive_errors': 0,       # consecutive error detections
    'consecutive_stale': 0,        # consecutive stale (no heartbeat) detections
    'total_recoveries': 0,
    'total_restarts': 0,
    'total_checks': 0,
    'last_restart_time': 0,
    'last_problem': '',
    'last_error_detail': '',
    'recovery_history': [],        # list of (timestamp, problem, result)
}

# === Defaults (overridden by CLI args) ===
CHECK_INTERVAL = 15
STALE_TIMEOUT = 45   # Y3 log has ~27s I/O buffer delay + 5s heartbeat + margin
MAX_CONSECUTIVE_ERRORS = 3
RESTART_COOLDOWN = 180


def log(msg, level='INFO'):
    """Write to report file and stdout (ASCII only for Windows compatibility)"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{timestamp}] [{level}] {msg}'
    print(line, flush=True)
    try:
        with open(REPORT_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def is_game_running():
    """Check if game process (Game_x64h) is alive"""
    try:
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-Process Game_x64h -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'],
            capture_output=True, text=True, startupinfo=startupinfo, timeout=10
        )
        pids = result.stdout.strip()
        return bool(pids), pids
    except Exception as e:
        return False, str(e)


def get_log_info():
    """Get log file metadata"""
    try:
        if not os.path.exists(LOG_FILE):
            return {'exists': False, 'mtime': 0, 'size': 0}
        stat = os.stat(LOG_FILE)
        return {
            'exists': True,
            'mtime': stat.st_mtime,
            'size': stat.st_size,
        }
    except Exception:
        return {'exists': False, 'mtime': 0, 'size': 0}


def count_errors_in_log():
    """Count [error] occurrences in log file"""
    try:
        if not os.path.exists(LOG_FILE):
            return 0
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return len(re.findall(r'\[error\]', content, re.IGNORECASE))
    except Exception:
        return 0


def check_heartbeat_in_log(stale_timeout=15):
    """Check if a recent [HEARTBEAT] exists in log by parsing timestamps.

    The game prints [HEARTBEAT] every 5s. This function finds the MOST RECENT
    [HEARTBEAT] line, parses its timestamp, and checks if it's within
    stale_timeout seconds of the current time.

    This avoids the false-positive bug where old [HEARTBEAT] lines remain
    in the log after the game freezes (the file stops updating but the
    old heartbeat lines are still there).

    Log timestamp format: [MM-DD HH:MM:SS.mmm]

    Returns:
        bool: True if recent heartbeat found (game alive), False if stale (game stuck)
    """
    try:
        if not os.path.exists(LOG_FILE):
            return False
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Find the last [HEARTBEAT] line (search from end)
        last_hb_line = None
        for line in reversed(lines):
            if '[HEARTBEAT]' in line:
                last_hb_line = line
                break

        if last_hb_line is None:
            return False  # no heartbeat ever found

        # Parse timestamp: [MM-DD HH:MM:SS.mmm]
        ts_match = re.match(r'\[(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})', last_hb_line)
        if not ts_match:
            return False

        now = datetime.now()
        month = int(ts_match.group(1))
        day = int(ts_match.group(2))
        hour = int(ts_match.group(3))
        minute = int(ts_match.group(4))
        second = int(ts_match.group(5))

        hb_time = now.replace(month=month, day=day, hour=hour, minute=minute, second=second, microsecond=0)
        diff = (now - hb_time).total_seconds()

        # If diff is negative (clock skew or year rollover), treat as alive
        if diff < 0:
            return True

        alive = diff <= stale_timeout
        if not alive:
            log(f'Heartbeat stale: last_hb={hb_time.strftime("%H:%M:%S")} now={now.strftime("%H:%M:%S")} diff={diff:.1f}s > threshold={stale_timeout}s', 'DEBUG')
        return alive
    except Exception as e:
        log(f'Heartbeat check error: {e}', 'ERROR')
        return True  # assume alive on read failure


def get_recent_errors(count=5):
    """Get most recent error lines from log"""
    try:
        if not os.path.exists(LOG_FILE):
            return []
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        errors = [line.strip() for line in lines if '[error]' in line.lower()]
        return errors[-count:]
    except Exception:
        return []


def run_game_control(cmd, timeout=60):
    """Execute game_control.py command"""
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, 'game_control.py')] + cmd.split(),
            capture_output=True, text=True, timeout=timeout, cwd=SCRIPT_DIR
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, 'command timeout'
    except Exception as e:
        return False, str(e)


def can_restart():
    """Check restart cooldown"""
    elapsed = time.time() - state['last_restart_time']
    return elapsed >= RESTART_COOLDOWN


def attempt_continue():
    """Try to recover with continue command"""
    log('Attempting continue recovery...', 'RECOVER')
    ok, output = run_game_control('c')
    if ok:
        state['total_recoveries'] += 1
        log('Continue command sent successfully', 'RECOVER')
        return True
    log(f'Continue failed: {output[:200]}', 'RECOVER')
    return False


def attempt_continue_and_verify():
    """Continue + verify heartbeat resumes (for stale/freeze recovery)"""
    log('Attempting continue + verify heartbeat resumes...', 'RECOVER')
    ok, output = run_game_control('c')
    if not ok:
        log(f'Continue failed: {output[:200]}', 'RECOVER')
        return False

    # Wait and check if heartbeat actually resumed (not just mtime change)
    log('Waiting 10s to verify heartbeat resumes...', 'RECOVER')
    time.sleep(10)
    if check_heartbeat_in_log(stale_timeout=STALE_TIMEOUT):
        state['total_recoveries'] += 1
        state['consecutive_stale'] = 0
        log_info = get_log_info()
        state['last_log_mtime'] = log_info.get('mtime', 0)
        state['last_log_size'] = log_info.get('size', 0)
        log('Heartbeat resumed after continue', 'RECOVER')
        return True

    log('Heartbeat still missing after continue', 'RECOVER')
    return False


def attempt_frestart():
    """Try full restart recovery"""
    if not can_restart():
        remaining = int(RESTART_COOLDOWN - (time.time() - state['last_restart_time']))
        log(f'Restart on cooldown, {remaining}s remaining', 'WARN')
        return False

    log('Attempting frestart (full restart)...', 'RECOVER')
    ok, output = run_game_control('frestart', timeout=120)
    if not ok:
        log(f'Frestart failed: {output[:200]}', 'ERROR')
        return False

    state['last_restart_time'] = time.time()
    state['total_restarts'] += 1

    log('Waiting 20s for game to load...', 'RECOVER')
    time.sleep(20)

    # Reset baselines after restart
    state['consecutive_errors'] = 0
    state['consecutive_stale'] = 0
    state['last_error_count'] = count_errors_in_log()
    log_info = get_log_info()
    state['last_log_mtime'] = log_info.get('mtime', 0)
    state['last_log_size'] = log_info.get('size', 0)

    log('Frestart completed, baselines reset', 'RECOVER')
    return True


def decide_recovery_strategy(problem_type, details):
    """Decide which recovery strategy to use based on problem type and history.

    Strategy logic:
    - crashed: Process is dead, continue is useless -> frestart only
    - error:   Lua error may trigger debugger breakpoint -> try continue first,
               escalate to frestart if continue keeps failing
    - stale:   Frozen game could be breakpoint or deadlock -> try continue+verify,
               escalate to frestart if log doesn't resume

    Uses state history to skip actions that have already failed recently.

    Args:
        problem_type: One of 'error', 'crashed', 'stale'
        details: String with problem details

    Returns:
        list of (str, callable) tuples: recovery actions to try in order
    """
    if problem_type == 'crashed':
        # Process is dead — continue has nothing to talk to
        return [('frestart', attempt_frestart)]

    if problem_type == 'error':
        # Lua errors often trigger Y3's debugger breakpoint.
        # continue releases the breakpoint so the game resumes.
        # But if we've already failed continue multiple times in a row,
        # skip straight to frestart.
        # Check if the last 2 history entries are both error+continue+FAIL
        # (must be the most recent — a success in between resets this)
        tail = state['recovery_history'][-2:]
        if len(tail) == 2 and all(
            prob == 'error' and action == 'continue' and result == 'FAIL'
            for _, prob, action, result in tail
        ):
            log('Skipping continue (last 2 attempts failed), going to frestart', 'RECOVER')
            return [('frestart', attempt_frestart)]
        return [('continue', attempt_continue), ('frestart', attempt_frestart)]

    if problem_type == 'stale':
        # Game frozen: could be breakpoint (continue fixes it) or real deadlock.
        # Use the verify variant that checks if log actually resumes.
        # If we've been stale many times in a row, skip to frestart.
        if state['consecutive_stale'] >= 3:
            log('Stale 3+ consecutive times, going straight to frestart', 'RECOVER')
            return [('frestart', attempt_frestart)]
        return [('continue_verify', attempt_continue_and_verify), ('frestart', attempt_frestart)]

    # Unknown problem type — try everything
    return [('continue', attempt_continue), ('frestart', attempt_frestart)]


def attempt_recovery(problem_type, details):
    """Execute recovery strategy and track results.

    Uses decide_recovery_strategy() to get the ordered list of actions,
    then tries each one until success or all fail.

    Returns:
        bool: True if recovery succeeded, False if all actions failed
    """
    log(f'Recovery needed [{problem_type}]: {details}', 'RECOVER')
    state['last_problem'] = problem_type
    state['last_error_detail'] = details

    strategy = decide_recovery_strategy(problem_type, details)

    for action_name, action_func in strategy:
        log(f'Trying recovery action: {action_name}', 'RECOVER')
        success = action_func()

        record = (datetime.now().strftime('%H:%M:%S'), problem_type, action_name,
                  'OK' if success else 'FAIL')
        state['recovery_history'].append(record)
        # Keep only last 20 records
        if len(state['recovery_history']) > 20:
            state['recovery_history'] = state['recovery_history'][-20:]

        if success:
            state['consecutive_failures'] = 0
            log(f'Recovery succeeded with: {action_name}', 'RECOVER')
            return True

    # All actions failed
    state['consecutive_failures'] += 1
    log(f'All recovery actions failed (consecutive failures: {state["consecutive_failures"]})', 'ERROR')
    return False


def check_cycle():
    """Execute one monitoring cycle. Returns True to continue, False to exit."""
    state['total_checks'] += 1

    # 1. Check game process
    running, pids = is_game_running()
    if not running:
        log(f'Game process not running! ({pids})', 'ERROR')
        state['consecutive_errors'] += 1
        if not attempt_recovery('crashed', f'process not found: {pids}'):
            return state['consecutive_failures'] < max_failures
        return True

    # 2. Check log file exists
    log_info = get_log_info()
    if not log_info['exists']:
        log('Log file does not exist', 'WARN')
        return True

    # 3. Check for new [error] entries
    error_count = count_errors_in_log()
    new_errors = error_count - state['last_error_count']
    if new_errors > 0:
        recent = get_recent_errors(min(new_errors, 5))
        log(f'Detected {new_errors} new error(s)!', 'ERROR')
        for err in recent:
            log(f'  >> {err[:200]}', 'ERROR')
        state['last_error_count'] = error_count
        state['consecutive_errors'] += 1
        state['last_error_detail'] = recent[-1] if recent else 'unknown'

        if state['consecutive_errors'] >= MAX_CONSECUTIVE_ERRORS:
            log(f'Consecutive error threshold reached ({state["consecutive_errors"]}), attempting recovery', 'WARN')
            if not attempt_recovery('error', f'{new_errors} new errors'):
                return state['consecutive_failures'] < max_failures
    else:
        state['consecutive_errors'] = 0

    # 4. Heartbeat check (timestamp-based)
    # The game prints [HEARTBEAT] every 5s. We parse the timestamp of the
    # most recent [HEARTBEAT] line and compare with current time.
    # If the last heartbeat is older than STALE_TIMEOUT, the game is frozen.
    has_heartbeat = check_heartbeat_in_log(stale_timeout=STALE_TIMEOUT)
    if has_heartbeat:
        state['consecutive_stale'] = 0
    else:
        stale_seconds = time.time() - log_info['mtime']
        state['consecutive_stale'] += 1
        log(f'Heartbeat stale! Last [HEARTBEAT] > {STALE_TIMEOUT}s ago, log mtime {int(stale_seconds)}s ago (consecutive: {state["consecutive_stale"]})', 'WARN')
        if not attempt_recovery('stale', f'heartbeat stale > {STALE_TIMEOUT}s, log {int(stale_seconds)}s ago'):
            return state['consecutive_failures'] < max_failures

    # 5. Periodic status report (every 10 checks)
    if state['total_checks'] % 10 == 0:
        elapsed = time.time() - state['start_time']
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        log(
            f'--- Status [{hours}h{minutes}m] --- '
            f'checks: {state["total_checks"]} | '
            f'errors: {error_count} | '
            f'recoveries: {state["total_recoveries"]} | '
            f'restarts: {state["total_restarts"]} | '
            f'consecutive_failures: {state["consecutive_failures"]}',
            'STATUS'
        )

    return True


def print_exit_report(reason, exit_code):
    """Print structured exit report that Claude can parse"""
    elapsed = time.time() - state['start_time']
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)

    # Build recovery history summary
    history_lines = []
    for ts, prob, action, result in state['recovery_history'][-5:]:
        history_lines.append(f'  {ts} | {prob} | {action} -> {result}')
    history_text = '\n'.join(history_lines) if history_lines else '  (none)'

    report = f"""
=== GAME WATCHDOG {'ALERT' if exit_code != 0 else 'SHUTDOWN'} ===
Reason: {reason}
Exit code: {exit_code}
Runtime: {hours}h{minutes}m
Total checks: {state['total_checks']}
Total recoveries: {state['total_recoveries']}
Total restarts: {state['total_restarts']}
Consecutive failures: {state['consecutive_failures']}
Last problem: {state['last_problem'] or 'none'}
Last error: {state['last_error_detail'][:300] if state['last_error_detail'] else 'none'}

Recent recovery history:
{history_text}

Log file: {os.path.abspath(LOG_FILE)}
Report: {os.path.abspath(REPORT_FILE)}
{'Action needed: Check game state, fix the error, then restart watchdog' if exit_code != 0 else 'No action needed (normal shutdown)'}
{'=' * 40}
"""
    print(report, flush=True)
    log(report.strip(), 'ALERT' if exit_code != 0 else 'INFO')


def main():
    global max_failures

    parser = argparse.ArgumentParser(description='Game Watchdog for Claude Code background monitoring')
    parser.add_argument('--max-failures', type=int, default=3,
                        help='Exit after N consecutive recovery failures (default: 3)')
    parser.add_argument('--timeout', type=int, default=86400,
                        help='Max runtime in seconds before normal exit (default: 86400 = 24h)')
    parser.add_argument('--check-interval', type=int, default=15,
                        help='Seconds between health checks (default: 15)')
    parser.add_argument('--stale-timeout', type=int, default=45,
                        help='Seconds since last heartbeat before declaring stale (default: 45, accounts for ~27s Y3 log buffer delay)')
    args = parser.parse_args()

    max_failures = args.max_failures
    global CHECK_INTERVAL, STALE_TIMEOUT
    CHECK_INTERVAL = args.check_interval
    STALE_TIMEOUT = args.stale_timeout

    state['start_time'] = time.time()
    state['last_error_count'] = count_errors_in_log()

    log_info = get_log_info()
    state['last_log_mtime'] = log_info.get('mtime', 0)
    state['last_log_size'] = log_info.get('size', 0)

    log('=' * 50)
    log('Game Watchdog started')
    log(f'  max_failures={max_failures} | timeout={args.timeout}s | interval={CHECK_INTERVAL}s | stale={STALE_TIMEOUT}s')
    log(f'  log: {os.path.abspath(LOG_FILE)}')
    log(f'  baseline errors: {state["last_error_count"]} (will be ignored)')
    log('=' * 50)

    # === Startup phase: wait for game to be healthy before monitoring ===
    # This prevents false positives during game loading/restart
    log('Waiting for game to become healthy (heartbeat check)...', 'STARTUP')
    startup_deadline = time.time() + 120  # max 2 min wait
    while time.time() < startup_deadline:
        running, _ = is_game_running()
        if running and check_heartbeat_in_log(stale_timeout=STALE_TIMEOUT):
            log('Game is healthy, starting monitoring loop', 'STARTUP')
            # Re-baseline after confirming healthy
            state['last_error_count'] = count_errors_in_log()
            log_info = get_log_info()
            state['last_log_mtime'] = log_info.get('mtime', 0)
            state['last_log_size'] = log_info.get('size', 0)
            break
        time.sleep(5)
    else:
        log('Game did not become healthy within 120s, starting monitoring anyway', 'WARN')

    deadline = state['start_time'] + args.timeout

    try:
        while True:
            # Check timeout
            if time.time() >= deadline:
                print_exit_report('Timeout reached (normal shutdown)', 0)
                sys.exit(0)

            # Run health check
            should_continue = check_cycle()

            if not should_continue:
                print_exit_report(
                    f'Auto-recovery failed {max_failures} consecutive times. '
                    f'Last problem: {state["last_problem"]} - {state["last_error_detail"][:200]}',
                    1
                )
                sys.exit(1)

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print_exit_report('Stopped by user (Ctrl+C)', 0)
        sys.exit(0)
    except Exception as e:
        print_exit_report(f'Unexpected error: {e}', 2)
        sys.exit(2)


if __name__ == '__main__':
    main()
