---
name: y3-game-test
description: Y3 ORPG游戏热更新与测试工具。通过 Y3 Helper 发送热更新命令、执行 Lua 代码。当用户需要测试Y3游戏功能或热更新代码时使用此技能。
---
# Y3 Game Test Skill

通过 Y3 Helper 实现游戏启动、热更新和远程执行 Lua 代码。

## 📚 开始前必读：Memory 记忆系统

**⚠️ 强制要求：开始测试工作前必须阅读相关记忆文件！**

记忆文件位于 `memory/` 目录，包含积累的测试经验和避坑指南：

| 文件 | 必读级别 | 适用场景 |
|------|---------|---------|
| `memory/main.md` | ⭐⭐⭐ **必读** | 每次测试工作开始前（游戏启动后必须 enter！） |
| `memory/skill-test.md` | ⭐⭐ 按需 | 测试 Lua 技能代码 |
| `memory/ui-test.md` | ⭐⭐ 按需 | 测试 UI 模块（改 UI 必须重启！） |
| `memory/equip-test.md` | ⭐⭐ 按需 | 测试装备系统 |

**工作流程**：
```
1. 阅读 memory/main.md（必读！）
2. 根据测试类型阅读相关记忆文件
3. 执行测试
4. 如有新经验，更新记忆文件
```

> ⚠️ **Memory 需要用户自行维护**：记忆文件需要根据实际项目情况修改补充。

---

## 🚨🚨🚨 强制要求：必须先启动监听器！🚨🚨🚨

**在执行任何游戏操作之前，必须先启动错误监听器！这是强制要求，不是可选的！**

```bash
cd <项目路径>/tools

# ████ 第1步：启动监听器（必须！否则看不到任何错误！）████
python file_listener.py &
# 或在新终端窗口运行: python file_listener.py
```

**不启动监听器的后果：**
- ❌ 看不到游戏端的 print/log 输出
- ❌ 看不到引擎级异常（如 "attempt to call a nil value"）
- ❌ 无法判断命令是否执行成功
- ❌ 调试时完全盲目

## 🚀 标准启动流程

```bash
cd <项目路径>/tools

# 1. 启动监听器（必须先做！）
python file_listener.py &

# 2. 启动游戏
python game_control.py launch

# 3. 等待加载（约15-30秒）
sleep 20

# 4. 进入游戏
python game_control.py enter

# 5. 等待进入（约8秒）
sleep 8

# 6. 验证（监听器应该显示打印内容）
python game_control.py lua "print('[test] 游戏已就绪')"
```

## ⚠️ 前提条件

1. **Cursor/VSCode 必须已打开项目** - Y3 Helper 插件在编辑器中运行
2. **首次使用需要安装配置** - 参见 `Y3_HELPER_SETUP.md`

## 功能速查

| 功能 | game_control.py 命令 |
|------|---------------------|
| 启动游戏 | `python game_control.py launch` |
| 执行 Lua 脚本 | `python game_control.py run <脚本>` |
| 执行 Lua 代码 | `python game_control.py lua "代码"` |
| 执行 Lua（无确认） | `python game_control.py lua-nc "代码"` |
| 快速进入 | `python game_control.py enter` |
| 检查状态 | `python game_control.py status` |
| 强制杀游戏 | `python game_control.py kill` |
| 强制重启 | `python game_control.py frestart` |

### ⭐ lua 命令默认带确认

`lua` 命令现在默认等待游戏端确认执行，解决了"命令发送成功但游戏卡死"的问题：

```bash
# 执行 Lua 代码（默认带确认，5秒超时）
python game_control.py lua "print('test')"
# 输出: [成功] 游戏已执行命令
# 或:   [失败] 未收到响应（可能游戏卡死）

# 无确认模式（旧行为，不等待响应）
python game_control.py lua-nc "print('test')"
```

**确认机制优势**：
- 明确知道命令是否真正执行
- 游戏卡死时立即得到反馈
- 自动化测试更可靠

### 调试控制命令

| 功能 | 命令 | 快捷 |
|------|------|------|
| **继续运行** | `continue` | `c` |
| 单步跳过 | `stepover` | `n` |
| 单步进入 | `stepinto` | `s` |
| 单步跳出 | `stepout` | `o` |
| 断点执行 | `break "代码"` | - |

> **首次使用前必须创建计划任务**（以管理员身份运行）：
> - `setup_launch_task.bat` - 创建启动游戏任务（无UAC弹窗启动）
> - `setup_kill_task.bat` - 创建杀进程任务（kill/frestart 需要）
>
> 不创建计划任务也能用，但会弹UAC确认框。

## 🚨 异常处理流程（重要！）

当遇到引擎级异常（如 "attempt to call a nil value"）时，游戏会卡在断点。

### 🔍 查看异常信息（必做！）

**游戏卡住时，第一步永远是查看异常消息文件：**

```bash
# 查看最近的异常和错误消息
tail -20 "$TEMP/y3helper_messages.jsonl"

# 或用 grep 过滤异常
grep "exception\|error" "$TEMP/y3helper_messages.jsonl" | tail -10
```

> ⚠️ **异常信息在消息文件里，不在游戏日志里！** 引擎级异常通过 Y3 Helper 补丁捕获，写入 `%TEMP%/y3helper_messages.jsonl`

### ⭐ 推荐流程：渐进式恢复

当命令执行无响应或疑似卡住时：

```bash
# 第1步：先查看异常信息（了解问题原因）
tail -20 "$TEMP/y3helper_messages.jsonl"

# 第2步：尝试继续运行（从异常恢复）
python game_control.py c

# 第3步：如果还是不行，强制重启
python game_control.py frestart
```

### 完整调试循环

```bash
# 1. 让游戏继续运行（从异常恢复）
python game_control.py c

# 2. 修复代码中的问题
# ...编辑代码...

# 3. 再次测试
python game_control.py run test_script
```

> 注意：`reload` 命令（热更新 base.hotfresh）已移除，因为大部分需要热更新的场景（UI、初始化代码）都不生效，直接用 `frestart` 重启更可靠。

**优势**：不需要重启游戏，保持游戏状态，调试效率最高！

### 备用流程：强制重启（当热更新无法生效时）

```bash
# 一键强制重启：杀进程 -> 启动 -> 等待 -> 进入
python game_control.py frestart
```

**适用场景**：
- 修改了 UI 事件回调
- 修改了模块初始化代码
- 游戏状态已损坏需要重置
- 多次尝试 continue 仍无响应

### 手动断点调试

```bash
# 方式1：在代码中设置断点执行
python game_control.py break "local x = some_func(); print(x)"

# 单步调试
python game_control.py n   # 单步跳过
python game_control.py s   # 单步进入
python game_control.py o   # 单步跳出

# 继续运行
python game_control.py c
```

**提示**：在 Lua 代码中直接调用 `dbg()` 也可以触发断点。

## 错误捕获系统

### 消息文件位置

所有错误都会写入：`%TEMP%\y3helper_messages.jsonl`

### 消息类型

1. **print 消息** - 游戏端的 print/log 输出
   ```json
   {"type":"print","level":"error","message":"[error] xxx","timestamp":"..."}
   ```

2. **调试器异常** - 引擎级异常（调用 nil 等）
   ```json
   {"type":"exception","level":"error","message":"attempt to call a nil value","timestamp":"..."}
   ```

### 检查错误的方法

```bash
# 方法1：检查日志文件（Lua层错误）
grep "\[error\]" .log/lua_player01.log

# 方法2：检查消息文件（所有错误，包括引擎异常）
grep "exception\|error" "$TEMP/y3helper_messages.jsonl" | tail -10

# 方法3：实时监听（推荐）
python file_listener.py
```

### 错误捕获架构

```
游戏端                      Y3 Helper 扩展                    消息文件
   │                             │                              │
   ├─ print/log消息 ──────────► registerMethod("print") ──────► jsonl
   │                             │                              │
   └─ 引擎异常 ──► lua-debug ──► DebugAdapterTracker ─────────► jsonl
```

## 调试流程

### 标准调试流程

1. **写调试脚本** → `tools/debug_xxx.lua`
2. **执行** → `python game_control.py run debug_xxx`
3. **查看日志** → `.log/lua_player01.log`
4. **检查错误** → `grep "[error]" .log/lua_player01.log`

### 快速代码测试

```bash
# 直接执行 Lua 代码（会用 xpcall 包装）
python game_control.py lua "print('test'); local x = some_func()"
```

### 调试脚本模板

```lua
-- tools/debug_xxx.lua
local player = y3.player(1)
local save = player:get_current_save()

print('===== 调试 =====')
print('字段A:', save.fieldA)
```

## 热更新生效条件

### ✅ 能生效
- `tools/xxx.lua` 测试脚本
- 数据表/配置修改

### ❌ 不生效（需重启）
- UI 事件回调 (`ui:bindEvent`)
- 模块初始化代码 (`M.init()`)
- `Initui` 注册的函数

**经验法则**：改了 `uimods/`、`mapwork/ui/` → 直接重启游戏

## 💓 心跳监控器（长时间运行必备）

### 核心原理

游戏卡在调试器断点时，**所有日志停止写入**，file_listener 无法检测。唯一可靠的检测方式是**心跳**：定期发送 Lua 命令，超时则判定游戏冻结。

### 启动心跳监控

```bash
cd <项目路径>/tools

# 后台启动心跳监控器（默认每10秒检测，5秒超时）
python heartbeat_monitor.py &

# 自定义间隔
python heartbeat_monitor.py --interval 5 &
```

### 心跳监控器功能

1. **冻结检测**：定期发送 `print('[HEARTBEAT]')` 到游戏，超时 = 冻结
2. **自动恢复**：检测到冻结后自动发送 `continue` 命令解除断点
3. **错误捕获**：恢复后自动检查 `y3helper_messages.jsonl` 中的异常和 `.log/lua_player01.log` 中的 `[error]`
4. **持续监控**：即使游戏正常运行，也会监控新增的日志错误和异常
5. **统计报告**：退出时输出心跳成功率、冻结次数、恢复次数等统计

### 单次检测模式

```bash
# 检测一次并输出 JSON 结果（用于外部脚本集成）
python heartbeat_monitor.py --once
# 输出: {"alive": true, "recovered": false, "errors": []}
# 退出码: 0=存活, 1=不存活
```

### 监控日志

所有监控事件记录在 `.log/monitor_errors.log`，包含：
- 心跳超时警告
- 冻结检测和恢复过程
- 捕获的异常和错误详情

### 🚨 长时间运行（过夜）标准流程

```bash
cd <项目路径>/tools

# 1. 启动游戏
python game_control.py launch
sleep 20
python game_control.py enter
sleep 8

# 2. 启动心跳监控器（必须！）
python heartbeat_monitor.py --interval 10 &

# 3. 启动业务逻辑
python game_control.py lua "print('[test] ready')"

# 4. 第二天检查：
cat ../.log/monitor_errors.log   # 查看监控日志
grep "\[error\]" ../.log/lua_player01.log  # 查看游戏错误
```

### 为什么不用 file_listener？

| 场景 | file_listener | heartbeat_monitor |
|------|:---:|:---:|
| 游戏正常运行时的日志 | ✅ 实时显示 | ✅ 检测新错误 |
| Lua xpcall 捕获的错误 | ✅ 显示 | ✅ 检测 |
| 引擎断点冻结（nil访问等） | ❌ **无法检测** | ✅ **心跳超时检测** |
| 自动恢复（continue） | ❌ 不支持 | ✅ 自动发送 |
| 错误详情（恢复后） | ❌ 不知道 | ✅ 检查异常+日志 |

> **结论**：长时间无人值守运行时，必须使用 `heartbeat_monitor.py`。`file_listener.py` 适合交互式调试时查看实时输出。

## 核心 API

```python
import socket, struct, json, re

def read_port():
    with open('log/helper_port.lua', 'r') as f:
        return int(re.search(r'return\s*(\d+)', f.read()).group(1))

def send_y3helper(command, args=None):
    port = read_port()
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

# 启动游戏
send_y3helper('y3-helper.launchGame')

# 热更新
send_y3helper('y3-helper.reloadLua')

# 执行测试脚本
send_y3helper('y3-helper.runLua', ["_reloadlua('tools.my_test')"])
```

## WSL 注意事项

必须使用 Windows Python 连接 Windows 端口：

```bash
/mnt/c/Windows/py.exe script.py
```

## 相关文件

| 文件 | 说明 |
|------|------|
| `Y3_HELPER_SETUP.md` | 安装配置指南 |
| `tools/game_control.py` | 游戏控制脚本 |
| `tools/heartbeat_monitor.py` | 心跳监控器（冻结检测+自动恢复） |
| `tools/file_listener.py` | 消息文件监听器（实时日志查看） |
| `tools/error_sender.lua` | 游戏端错误发送模块 |
