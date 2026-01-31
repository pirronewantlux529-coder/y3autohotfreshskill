---
name: y3-game-test
description: Y3 ORPG游戏热更新与测试工具。通过 Y3 Helper 发送热更新命令、执行 Lua 代码。当用户需要测试Y3游戏功能或热更新代码时使用此技能。
---
# Y3 Game Test Skill

通过 Y3 Helper 实现游戏启动、热更新和远程执行 Lua 代码。

## ⚠️ 前提条件

1. **Cursor/VSCode 必须已打开项目** - Y3 Helper 插件在编辑器中运行
2. **首次使用需要安装配置** - 参见 `Y3_HELPER_SETUP.md`

## 🚀 启动游戏标准流程（必读！）

**启动游戏前必须先开启监听器！**

```bash
cd <项目路径>/tools

# 第1步：后台启动监听器（捕获错误消息）
python file_listener.py &

# 第2步：启动游戏
python game_control.py launch

# 第3步：等待加载（约30秒）
sleep 30

# 第4步：进入游戏
python game_control.py enter

# 第5步：验证是否进入成功（看监听器是否有打印输出）
python game_control.py lua "print('[test] 游戏已就绪')"
```

> ⚠️ **不开监听器 = 看不到错误！** 监听器会实时显示游戏端的 print/log 和引擎异常。
>
> 💡 **判断是否进入游戏**：发送 lua 命令，如果监听器显示打印内容则说明已进入。

## 功能速查

| 功能 | game_control.py 命令 |
|------|---------------------|
| 启动游戏 | `python game_control.py launch` |
| 热更新 | `python game_control.py reload` |
| 执行 Lua 脚本 | `python game_control.py run <脚本>` |
| 执行 Lua 代码 | `python game_control.py lua "代码"` |
| 快速进入 | `python game_control.py enter` |
| 检查状态 | `python game_control.py status` |
| 强制杀游戏 | `python game_control.py kill` |
| 强制重启 | `python game_control.py frestart` |

### 调试控制命令

| 功能 | 命令 | 快捷 |
|------|------|------|
| **继续运行** | `continue` | `c` |
| 单步跳过 | `stepover` | `n` |
| 单步进入 | `stepinto` | `s` |
| 单步跳出 | `stepout` | `o` |
| 断点执行 | `break "代码"` | - |

> **注意**：`kill` 和 `frestart` 只杀游戏进程，不杀编辑器。首次使用需以管理员运行 `setup_kill_task.bat` 创建计划任务。

## 🚨 异常处理流程（重要！）

当遇到引擎级异常（如 "attempt to call a nil value"）时，游戏会卡在断点。

### ⭐ 推荐流程：渐进式恢复

当命令执行无响应或疑似卡住时，按以下顺序尝试：

```bash
# 第1步：再发一次命令（可能只是网络延迟）
python game_control.py run test_script

# 第2步：尝试继续运行（可能卡在断点/异常）
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

# 3. 热更新修复后的模块
python game_control.py reload module_name

# 4. 再次测试
python game_control.py run test_script
```

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
| `tools/file_listener.py` | 消息文件监听器 |
| `tools/error_sender.lua` | 游戏端错误发送模块 |
