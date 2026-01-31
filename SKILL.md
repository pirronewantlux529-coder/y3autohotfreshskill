---
name: y3-game-test
description: Y3 ORPG游戏热更新与测试工具。通过 Y3 Helper 发送热更新命令、执行 Lua 代码。当用户需要测试Y3游戏功能或热更新代码时使用此技能。
---
# Y3 Game Test Skill

通过 Y3 Helper 实现游戏启动、热更新和远程执行 Lua 代码。

## ⚠️ 前提条件

1. **Cursor/VSCode 必须已打开项目** - Y3 Helper 插件在编辑器中运行
2. **首次使用需要安装配置** - 参见 `Y3_HELPER_SETUP.md`

## 功能速查

| 功能 | Y3 Helper 命令 | game_control.py |
|------|----------------|-----------------|
| 启动游戏 | `y3-helper.launchGame` | - |
| 热更新 | `y3-helper.reloadLua` | `python game_control.py reload` |
| 执行 Lua | `y3-helper.runLua` | `python game_control.py run <脚本>` |
| 快速进入 | - | `python game_control.py enter` |
| 重启游戏 | - | `python game_control.py restart` |
| 宠物测试 | - | `python game_control.py pet` |

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

# 执行 Lua 代码
send_y3helper('y3-helper.runLua', ["print('Hello!')"])

# 执行测试脚本
send_y3helper('y3-helper.runLua', ["_reloadlua('tools.my_test')"])
```

## 调试流程

1. **写调试脚本** → `tools/debug_xxx.lua`
2. **执行** → `python game_control.py run debug_xxx`
3. **查看日志** → `.log/lua_player01.log`
4. **检查错误** → `grep "[error]" .log/lua_player01.log`

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

## 错误检测

### 方式1：日志文件检查

```bash
grep "\[error\]" .log/lua_player01.log
# 无输出 = 测试通过
# 有输出 = 必须修复
```

### 方式2：实时错误监听（推荐）

当错误不在日志文件中（如Y3 Helper发到Cursor的错误），使用错误监听器：

```bash
# 启动监听器
python error_listener.py
```

**error_sender 会随游戏启动自动加载**（通过 debugs.lua），无需手动执行。

只需保持监听器运行，所有错误会实时显示。

### 错误监听架构

```
游戏端                    Python监听器
   │                          │
   ├─ error_sender.lua        │
   │   hook log.error         │
   │         │                │
   │         ▼                │
   └──► socket:12999 ────────►│ 实时显示错误
                              │
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
| `examples/y3helper_client.py` | Python 客户端库 |
