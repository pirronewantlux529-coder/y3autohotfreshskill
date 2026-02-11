---
name: y3-game-test
description: 通过Y3 Helper执行Lua代码并自动检测错误，启动游戏、热更新模块、运行测试脚本。用于测试游戏功能、调试Lua代码、验证代码修改的任务。
---
# Y3游戏测试

通过Y3 Helper执行Lua并自动检测日志错误和异常。

## 🚨 核心铁律

### 每次发送Lua必须检查错误！

**使用 lua_executor 自动检查错误：**

```python
from lua_executor import execute_lua, print_result

result = execute_lua("your_code")
print_result(result)

if not result.success:
    exit(1)  # 失败时停止
```

**绝不能：**
- ❌ 发送代码后不检查就继续
- ❌ 用 `game_control.py lua` 后不查日志
- ❌ 假设"没报错=成功"

## 🚀 标准测试流程

### Python脚本（推荐）

```python
from lua_executor import execute_lua, execute_lua_file, print_result
import subprocess, time

# 1. 启动游戏
subprocess.run(['python', 'game_control.py', 'launch'])
time.sleep(20)

# 2. 进入游戏
result = execute_lua_file('quick_enter')
print_result(result)
if not result.success:
    exit(1)
time.sleep(8)

# 3. 执行测试
result = execute_lua("""
    local player = y3.player(1)
    print('[测试] 玩家:', player)
""")
print_result(result)
```

### 命令行（备用）

```bash
cd <项目路径>/tools

# 1. 启动
python game_control.py launch
sleep 20

# 2. 进入
python lua_executor.py --file quick_enter
sleep 8

# 3. 测试
python lua_executor.py "print('[test] ready')"
```

## 📚 API

### lua_executor 模块

```python
from lua_executor import execute_lua, execute_lua_file, print_result

# 执行Lua代码
result = execute_lua("lua_code", timeout=10)

# 执行tools/下的脚本
result = execute_lua_file('script_name', timeout=10)

# 显示结果
print_result(result, verbose=True)
```

**ExecuteResult 对象：**
- `success`: bool - 是否成功（无错误）
- `executed`: bool - 游戏是否响应
- `alive`: bool - 游戏是否存活
- `log_errors`: list - 日志错误列表
- `exceptions`: list - 异常列表
- `error`: str - 错误信息
- `warning`: str - 警告信息

### game_control.py 命令

| 命令 | 功能 |
|------|------|
| `launch` | 启动游戏 |
| `enter` | 进入游戏 |
| `kill` | 强制杀游戏进程 |
| `frestart` | 强制重启 |
| `status` | 检查游戏状态 |
| `c` / `continue` | 继续运行（从断点恢复） |
| `lua "代码"` | 执行Lua（带确认） |
| `run 脚本` | 执行tools/下的脚本 |

## 📝 测试代码模板

### 单步测试

```python
from lua_executor import execute_lua, print_result

result = execute_lua("""
    -- 测试代码
    print('[测试] xxx')
""")

print_result(result)
if not result.success:
    exit(1)
```

### 多步测试

```python
from lua_executor import execute_lua
import time

steps = [
    ("步骤1", "lua_code_1"),
    ("步骤2", "lua_code_2"),
]

for i, (desc, code) in enumerate(steps, 1):
    print(f'\n[{i}] {desc}')
    result = execute_lua(code)

    if not result.success:
        print(f'✗ 失败: {result.error}')
        if result.log_errors:
            for err in result.log_errors:
                print(f'  {err}')
        exit(1)

    print(f'✓ 成功')
    time.sleep(0.5)
```

## 💓 心跳监控器

**长时间运行时使用**（如压力测试、fakeplayer）

```bash
# 启动游戏
python game_control.py launch && sleep 20
python lua_executor.py --file quick_enter && sleep 8

# 启动心跳监控器（前台，实时显示）
python heartbeat_monitor.py --interval 10

# 或后台运行（配合 tail 查看）
python heartbeat_monitor.py --interval 10 > monitor.log 2>&1 &
tail -f monitor.log
```

**实时监控**：
- 控制台实时显示心跳状态、错误、恢复事件
- 发现错误立即打印，无需事后查日志
- 卡死时自动尝试恢复并显示结果
- 所有事件同时写入 `../.log/monitor_errors.log`

## 🔥 热更新生效条件

### 能生效
- `tools/` 下的测试脚本
- 数据表/配置修改

### 不生效（必须重启）
- UI 事件回调 (`ui:bindEvent`)
- 模块初始化 (`M.init()`)
- `Initui` 注册的函数
- 玩家初始化流程

**改了 `uimods/`、`mapwork/ui/` → 直接 `frestart` 重启**

## 🚨 异常处理

### 查看异常消息

```bash
# 查看最近的异常
tail -20 "$TEMP/y3helper_messages.jsonl"

# 过滤异常
grep "exception" "$TEMP/y3helper_messages.jsonl" | tail -10
```

### 从断点恢复

```bash
# 1. 游戏卡在断点，先查异常
tail -20 "$TEMP/y3helper_messages.jsonl"

# 2. 继续运行
python game_control.py c

# 3. 还是不行，强制重启
python game_control.py frestart
```

## 相关文件

| 文件 | 说明 |
|------|------|
| `tools/lua_executor.py` | 自动错误检测的执行器 |
| `tools/game_control.py` | 游戏控制脚本 |
| `tools/heartbeat_monitor.py` | 心跳监控器 |
| `tools/test_with_executor.py` | 使用示例 |
| `README_NEW_WORKFLOW.md` | 完整工作流程说明 |
