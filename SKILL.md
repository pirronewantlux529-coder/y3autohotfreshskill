---
name: y3-game-test
description: 通过Y3 Helper执行Lua代码并自动检测错误，启动游戏、热更新模块、运行测试脚本。用于测试游戏功能、调试Lua代码、验证代码修改的任务。
---
# Y3测试流程

Y3 Helper执行Lua代码，自动检测日志错误和异常。

## 🚨 最高铁律：没有打印 = 100%有错误！

**⚠️ 这条规则高于一切：**

- 执行 `run` 命令后，如果**没看到任何游戏内 print 输出** → 100%代码有错误
- "没有输出"不是"没有错误"，恰恰相反——代码在出错点就中断了，后面的 print 根本没执行到
- **必须立即检查日志**，分析错误原因并修复

### `run` 命令输出解读

| 输出 | 含义 | 操作 |
|------|------|------|
| `[RUN-OK]` | 脚本执行成功 | 继续下一步 |
| `[RUN-FAIL]` | 脚本执行失败 | **停止！分析错误详情，修复代码** |
| 没有任何 `[RUN-` 开头的行 | 游戏卡死/未响应 | 执行 `python game_control.py frestart` |
| Bash exit code 非零 | 命令失败 | **停止！不要忽略，分析输出中的错误** |

### `run` 命令只支持脚本文件名

```bash
# ✅ 正确：执行 tools/my_test.lua 脚本
python game_control.py run my_test

# ❌ 错误：run 不支持行内 Lua 代码
python game_control.py run "print('hello')"

# 需要行内代码用 lua 命令
python game_control.py lua "print('hello')"
```

## 🚨 核心铁律

### 命令中断检测与恢复流程

**`run` 命令已内置自动恢复**：心跳停止 → 自动 continue → 提取 `.lua:` 错误 → 返回 `[RUN-FAIL]`。

**如果自动恢复也失败：**
```bash
# 强制重启（自动 kill → launch → 等待 → enter）
python game_control.py frestart
# frestart 已内置进入游戏步骤，完成后即可执行命令
```

### 错误检测铁律

```bash
grep "\.lua:" .log/lua_player01.log | tail -20  # 捕获所有Lua错误
```

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
- ❌ 看到 Bash 输出中有报错信息却不分析，继续执行下一步
- ❌ 假设"没有打印=没有错误"——**恰恰相反！**
- ❌ Bash exit code 非零时不管不顾

## 标准测试流程

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

## Orders自动化命令库

### Orders目录结构

```
tools/orders/
├── game/          # 游戏操作（进入游戏、传送）
├── ui/            # UI操作（点击按钮、输入文本）
├── test/          # 测试辅助（给物品、设等级）
└── debug/         # 调试工具（打印状态、检查错误）
```

### 使用Orders

**Python脚本中**：
```python
from orders_manager import execute_order, OrderChain

# 执行单个命令
result = execute_order('game/enter_game')

# 带参数执行
result = execute_order('test/give_items', item_id=1001, count=10)

# 命令链（多步骤）
chain = OrderChain()
chain.add('game/enter_game')
chain.add('test/give_items', item_id=1001, count=10)
chain.add('test/set_level', level=30)
results = chain.execute()
```

**命令行**：
```bash
# 列出所有可用命令
python orders_manager.py list

# 执行命令
python orders_manager.py run game/enter_game

# 带参数
python orders_manager.py run test/give_items --item_id=1001 --count=10
```

### 常用Orders

| 命令 | 功能 | 参数 |
|------|------|------|
| `game/enter_game` | 自动进入游戏 | - |
| `ui/click_button` | 点击UI按钮 | ui_path, wait_time |
| `test/give_items` | 给予物品 | item_id, count |
| `test/set_level` | 设置等级 | level |
| `debug/print_state` | 打印游戏状态 | - |

### 自定义Order

创建 `orders/custom/my_command.lua`：
```lua
--[[
    命令：我的自定义命令
    功能：描述
    参数：param1, param2
]]

-- 参数
param1 = param1 or 'default'

print('[Order] 执行自定义命令')
-- 你的逻辑
return {success = true}
```

使用：
```bash
python orders_manager.py run custom/my_command --param1=value
```

## API参考

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
| `screenshot` / `ss` | 截取游戏窗口画面（不抢焦点） |

### ⚠️ run命令自动恢复（已实现）

**Lua语法错误 → 自动continue + 提取错误**

- 发送命令后等待5秒检查心跳（日志中的 `[HEARTBEAT]` 或 `AutoPlayer`）
- 心跳停止 → 自动 `debug_continue()` → 提取 `.lua:` 错误
- 返回 `success=False` 和错误详情

**无需手动操作，错误会自动提取并返回。**

## ⚠️ `run` 命令常见错误及规避

### 行内Lua代码语法陷阱

`game_control.py run "lua代码"` 会将字符串传给Y3引擎解析，以下写法**容易出错**：

```lua
-- ❌ 错误：h:method() 中括号被shell或Y3 wrap_code误解析
print('[状态] battle='..tostring(h:is_in_battle()))

-- ❌ 错误：~= 在字符串拼接中可能导致解析异常
tostring(h.timer~=nil)

-- ❌ 错误：直接使用 player 全局变量（tool脚本中不存在）
local h = player.mainhero
```

### ✅ 正确做法

**行内代码只适合极简语句**：
```bash
python game_control.py lua "print('hello')"
```

**超过一行 → 写成工具脚本文件**（推荐）：
```bash
# 创建 tools/my_test.lua
# 然后执行：
python game_control.py run my_test
```

**工具脚本中获取玩家对象**：
```lua
-- tools/my_test.lua
local p = y3.player(1)        -- ✅ 正确：通过y3.player获取
local h = p.mainhero           -- ✅ 正确
-- local h = player.mainhero   -- ❌ 错误：player不是全局变量
```

## 测试代码模板

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

## 心跳监控器

长时间运行时使用（压力测试、fakeplayer）：

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

## 📸 截图验证

### 截图命令

```bash
# 截取游戏画面（保存到 C:/screenshot_temp/game_screenshot.png）
python game_control.py screenshot

# 简写
python game_control.py ss

# 指定保存路径
python game_control.py ss C:/my_screenshots/test1.png
```

**Python 中调用：**
```python
from game_control import screenshot

path = screenshot()  # 返回保存路径，失败返回 None
```

### 什么时候需要截图验证？

日志检查只能验证"没有报错"，无法验证"画面效果正确"。

| 场景 | 仅查日志 | 需要截图 |
|------|---------|---------|
| 修改了 UI 布局/位置/大小 | ❌ 不够 | ✅ 必须截图看布局效果 |
| 修改了 UI 显示内容（文字/图标/颜色） | ❌ 不够 | ✅ 必须截图看显示效果 |
| 修改了特效/动画相关代码 | ❌ 不够 | ✅ 必须截图看视觉效果 |
| 新增了 UI 面板/窗口 | ❌ 不够 | ✅ 必须截图确认面板出现 |
| 修改了纯逻辑（属性计算、伤害公式） | ✅ 日志够了 | ⬜ 可选 |
| 修改了数据表（配置表）| ✅ 日志够了 | ⬜ 可选 |

### 截图验证标准流程

```bash
cd <项目路径>/tools

# 1. 修改代码后重启游戏
python game_control.py frestart
sleep 20

# 2. 日志检查（必须）
grep "\.lua:" ../.log/lua_player01.log | tail -20

# 3. 截图验证（UI相关修改必须执行）
python game_control.py ss

# 4. 查看截图确认画面效果
# 截图保存在 C:/screenshot_temp/game_screenshot.png
```

### 截图注意事项

- 截图会短暂将游戏窗口置前台（约0.5秒），随后自动切回
- 截图保存在 `C:/screenshot_temp/game_screenshot.png`（固定英文路径，避免编码问题）
- 如果截图失败，确认游戏窗口正在运行且未最小化
- 依赖安装：`pip install pywin32 dxcam Pillow`

## 热更新生效条件

### 能生效
- `tools/` 下的测试脚本
- 数据表/配置修改

### 不生效（必须重启）
- UI 事件回调 (`ui:bindEvent`)
- 模块初始化 (`M.init()`)
- `Initui` 注册的函数
- 玩家初始化流程

**改了 `uimods/`、`mapwork/ui/` → 直接 `frestart` 重启**

## 异常处理

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

## 🐕 Game Watchdog（后台持久监控）

### 原理

`game_watchdog.py` 作为 Claude Code 的后台 Task 运行（`run_in_background=true`）。它持续监控游戏健康状态，自动恢复大部分问题。**只有当自动恢复连续失败时**，脚本 exit(1)，Claude 自动收到通知。

### 启动 Watchdog

**⚠️ 启动顺序很重要：必须先确认游戏状态正常，再启动 watchdog！**

```bash
# 1. 先确认游戏正在运行且已进入
python game_control.py status

# 2. 后台启动 watchdog（watchdog 内置启动等待，会等心跳正常后才进入监控）
python tools/game_watchdog.py --max-failures 3
```

**Claude Code 中使用 `run_in_background=true`**：
```
# 先检查 status，确认游戏正常
Bash(command="python tools/game_control.py status")
# 再后台启动
Bash(command="python tools/game_watchdog.py --max-failures 3", run_in_background=true)
```

**Watchdog 启动阶段**：脚本启动后会先进入 STARTUP 等待阶段（最长120秒），轮询检测游戏心跳。只有检测到有效心跳后，才进入正式监控循环。这避免了游戏加载期间的误报。

### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-failures` | 3 | 连续恢复失败N次后 exit(1) 通知Claude |
| `--timeout` | 86400 | 最大运行时间(秒)，超时正常 exit(0) |
| `--check-interval` | 15 | 健康检查间隔(秒) |
| `--stale-timeout` | 45 | 最后心跳超时(秒)，判定卡死。Y3日志有~27s缓冲延迟，45s=延迟+容错 |

### Watchdog 自动恢复策略

| 问题类型 | 第一步 | 第二步 |
|----------|--------|--------|
| `crashed`（进程死亡） | 直接 frestart | — |
| `error`（Lua报错） | continue（释放断点） | frestart |
| `stale`（心跳超时） | continue + 验证心跳恢复 | frestart |

### Claude 收到 Watchdog 通知时

Watchdog exit(1) 的输出包含结构化报告：
```
=== GAME WATCHDOG ALERT ===
Reason: Auto-recovery failed 3 consecutive times
Last problem: error
Last error: xxx.lua:123: attempt to call nil
...
Action needed: Check game state, fix the error, then restart watchdog
```

**收到通知后必须：**
1. 阅读错误详情，定位问题
2. 修复代码
3. 手动 frestart 游戏
4. 重新启动 watchdog

### 检查 Watchdog 状态

```bash
# 非阻塞检查（不等待完成）
TaskOutput(task_id="watchdog_task_id", block=false)

# 查看报告文件
cat tools/watchdog_report.log | tail -20
```

## 相关文件

| 文件 | 说明 |
|------|------|
| `tools/lua_executor.py` | 自动错误检测的执行器 |
| `tools/game_control.py` | 游戏控制脚本 |
| `tools/game_watchdog.py` | 后台守护监控（Claude集成） |
| `tools/heartbeat_monitor.py` | 心跳监控器 |
| `tools/test_with_executor.py` | 使用示例 |
| `README_NEW_WORKFLOW.md` | 完整工作流程说明 |
