# Y3 Helper 调试环境安装向导

本文档是交互式安装指南，Claude Code 会根据此文档引导用户完成配置。

---

## 🔧 安装前检查

Claude 在开始安装前需要向用户确认以下信息：

### 问题 1：使用的编辑器
```
请问你使用的是哪个编辑器？
1. Cursor
2. VSCode
```

### 问题 2：项目路径
```
请确认你的 Y3 项目脚本目录路径（包含 main.lua 的目录）：
默认: D:\Y3\ORPG项目总包\ORPG\maps\EntryMap\script

请输入路径或按回车使用默认值：
```

### 问题 3：运行环境
```
你使用的是什么终端环境？
1. Windows CMD/PowerShell（推荐）
2. WSL (Windows Subsystem for Linux)
```

---

## 📋 安装步骤

### 步骤 1：检查 Y3 Helper 插件

Claude 执行：
```python
import os

# 根据用户选择的编辑器
editor = "cursor"  # 或 "vscode"
user_home = os.path.expanduser("~")

if os.name == 'nt':  # Windows
    ext_base = os.path.join(user_home, f".{editor}", "extensions")
else:  # WSL
    ext_base = f"/mnt/c/Users/Administrator/.{editor}/extensions"

# 查找 Y3 Helper
y3_helper_path = None
if os.path.exists(ext_base):
    for name in os.listdir(ext_base):
        if name.startswith("sumneko.y3-helper"):
            y3_helper_path = os.path.join(ext_base, name)
            break

if y3_helper_path:
    print(f"✓ 找到 Y3 Helper: {y3_helper_path}")
else:
    print("✗ 未找到 Y3 Helper 插件，请先在编辑器中安装")
```

**如果未找到插件**，提示用户：
```
请在 Cursor/VSCode 中安装 Y3 Helper 插件：
1. 打开扩展市场 (Ctrl+Shift+X)
2. 搜索 "Y3 Helper"
3. 安装 sumneko.y3-helper
4. 重启编辑器后再次运行安装
```

### 步骤 2：修改 Y3 Helper 插件（添加 runLua 命令）

Claude 执行 `tools/install_y3helper_runlua.py`：

```bash
# Windows
cd <项目路径>/tools
python install_y3helper_runlua.py

# WSL
cd <项目路径>/tools
/mnt/c/Windows/py.exe install_y3helper_runlua.py
```

**预期输出**：
```
找到插件：C:\Users\xxx\.cursor\extensions\sumneko.y3-helper-x.x.x\dist\extension.js
已备份到：extension.js.backup
✓ runLua 命令安装成功！
请重启 VSCode/Cursor 使修改生效
```

### 步骤 3：配置游戏端代码

Claude 检查 `base/debugs.lua` 是否包含 Y3 Helper 消息处理器：

```lua
-- 需要确保以下代码存在于 base/debugs.lua
if y3.develop and y3.develop.helper then
    local helper = y3.develop.helper
    helper.onReady(function()
        helper.registerMethod('command', function(params)
            if params and params.data then
                y3.develop.console.input(params.data)
            end
        end)
        print('[debugs] Y3 Helper command 处理器已注册')
    end)
end
```

如果不存在，Claude 从 `examples/debugs_y3helper_patch.lua` 复制代码到 `base/debugs.lua`。

### 步骤 4：创建工具目录和脚本

Claude 检查并创建必要文件：

```
<项目路径>/
├── tools/
│   ├── game_control.py      # 游戏控制脚本
│   ├── install_y3helper_runlua.py  # 插件安装脚本
│   ├── quick_enter.lua      # 快速进入游戏
│   ├── restart_game.lua     # 重启游戏
│   └── pet_test.lua         # 宠物测试（示例）
└── log/
    └── helper_port.lua      # Y3 Helper 端口（游戏运行时自动生成）
```

### 步骤 5：验证安装

Claude 执行验证：

```python
import socket
import struct
import json

# 1. 检查端口文件
port_file = "<项目路径>/log/helper_port.lua"
# 读取端口...

# 2. 测试连接
sock = socket.socket()
sock.settimeout(3)
try:
    sock.connect(('127.0.0.1', port))
    print("✓ Y3 Helper 连接成功")

    # 3. 发送测试命令
    msg = {
        'method': 'command',
        'id': 1,
        'params': {'command': 'y3-helper.runLua', 'args': ["print('[测试] Y3 Helper 安装成功!')"]}
    }
    data = json.dumps(msg).encode('utf-8')
    sock.send(struct.pack('>I', len(data)) + data)
    print("✓ 测试命令已发送，请查看游戏日志")
except ConnectionRefusedError:
    print("✗ 连接失败 - 请确保编辑器已打开并运行 Y3 Helper")
```

---

## ⚠️ WSL 特殊配置

如果用户使用 WSL 环境：

1. **必须以管理员权限运行 WSL**
2. **必须使用 Windows Python** 连接 Windows 端口：
   ```bash
   # 正确
   /mnt/c/Windows/py.exe script.py

   # 错误（无法连接 Windows 端口）
   python script.py
   ```

---

## 🔄 插件更新后重新安装

Y3 Helper 插件更新后，需要重新执行步骤 2：

```bash
python tools/install_y3helper_runlua.py
```

然后重启编辑器。

---

## 🐛 故障排除

### 问题：command 'y3-helper.runLua' not found
- 确认已运行 `install_y3helper_runlua.py`
- 确认已重启编辑器

### 问题：连接被拒绝
- 确认编辑器已打开项目
- 确认 Y3 Helper 插件已启动（查看编辑器底部状态栏）

### 问题：游戏收不到消息
- 确认游戏以调试模式启动（通过 Y3 Helper 启动）
- 检查 `base/debugs.lua` 中的代码是否正确
- 查看日志：`.log/lua_player01.log`

### 问题：端口文件不存在
- `log/helper_port.lua` 在游戏启动后自动生成
- 先通过 Y3 Helper 启动游戏

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `examples/debugs_y3helper_patch.lua` | debugs.lua 补丁代码 |
| `examples/y3helper_client.py` | Python 客户端库 |
| `examples/example_test.py` | 使用示例 |
| `tools/install_y3helper_runlua.py` | 插件安装脚本 |
| `tools/game_control.py` | 游戏控制主脚本 |

---

## ✅ 安装完成确认清单

Claude 在安装完成后确认：

- [ ] Y3 Helper 插件已安装
- [ ] runLua 命令已添加到插件
- [ ] debugs.lua 包含消息处理器
- [ ] 编辑器已重启
- [ ] 游戏能通过 `y3-helper.launchGame` 启动
- [ ] 热更新命令能正常工作
- [ ] 测试脚本能正常执行
