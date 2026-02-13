---
name: y3-game-test
description: 通过Y3 Helper执行Lua代码并自动检测错误，启动游戏、热更新模块、运行测试脚本。用于测试游戏功能、调试Lua代码、验证代码修改的任务。
---
# Y3测试流程

Y3 Helper执行Lua代码，自动检测日志错误和异常。

## 🚨 核心铁律

### 命令中断检测与恢复流程

**发送Lua命令后的检查流程：**

1. **发送命令后等待5-8秒**
2. **检查心跳包**（查看日志中是否有AutoPlayer状态报告）
3. **如果心跳停止** → 100%确定命令有错误：
   ```bash
   # Step 1: 继续游戏
   python game_control.py continue
   sleep 3

   # Step 2: 检查错误（使用 .lua: 而不是 [error]）
   grep "\.lua:" .log/lua_player01.log | tail -20

   # Step 3: 分析错误，修复代码
   # Step 4: 重新发送命令
   ```

4. **如果心跳正常但没输出** → 检查其他问题（文件路径、模块名等）

### 错误检测铁律

**❌ 错误的做法：**
```bash
grep "\[error\]" .log/lua_player01.log  # 只能捕获部分错误！
```

**✅ 正确的做法：**
```bash
grep "\.lua:" .log/lua_player01.log | tail -20  # 捕获所有Lua错误（.lua:行号格式）
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
- ❌ 用 `game_control.py lua` 后不查日志
- ❌ 假设"没报错=成功"
- ❌ 只查 `[error]` 而不查 `.lua:`

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

- 发送命令后等待5秒检查心跳（日志中的 `AutoPlayer`）
- 心跳停止 → 自动 `debug_continue()` → 提取 `.lua:` 错误
- 返回 `success=False` 和错误详情

**无需手动操作，错误会自动提取并返回。**

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

## 相关文件

| 文件 | 说明 |
|------|------|
| `tools/lua_executor.py` | 自动错误检测的执行器 |
| `tools/game_control.py` | 游戏控制脚本 |
| `tools/heartbeat_monitor.py` | 心跳监控器 |
| `tools/test_with_executor.py` | 使用示例 |
| `README_NEW_WORKFLOW.md` | 完整工作流程说明 |
