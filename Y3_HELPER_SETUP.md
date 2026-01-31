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

---

## 📋 安装步骤

### 步骤 1：检查 Y3 Helper 插件

Claude 执行：
```python
import os, glob

editor = "cursor"  # 或 "vscode"
user_home = os.path.expanduser("~")
ext_base = os.path.join(user_home, f".{editor}", "extensions")

# 查找 Y3 Helper
y3_helper_paths = glob.glob(os.path.join(ext_base, "sumneko.y3-helper-*"))
if y3_helper_paths:
    y3_helper_path = sorted(y3_helper_paths)[-1]  # 最新版本
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

### 步骤 2：安装 Y3 Helper 补丁（错误捕获）

Y3 Helper 需要打两个补丁来捕获所有错误：

#### 补丁 1：print 消息转发

```bash
cd <tools目录>
python patch_y3helper_http.py
```

**作用**：将游戏端的 print/log 消息写入文件，供外部监听。

#### 补丁 2：调试器异常捕获

```bash
cd <tools目录>
python patch_debugger_exception.py
```

**作用**：捕获引擎级异常（如 "attempt to call a nil value"），写入同一文件。

**预期输出**：
```
Y3 Helper 调试异常捕获补丁
==================================================
[找到] C:\Users\xxx\.cursor\extensions\sumneko.y3-helper-x.x.x
[备份] extension.js.backup.exception.xxx
[成功] 调试异常捕获补丁已应用
[提示] 异常消息将写入: C:\Users\xxx\AppData\Local\Temp\y3helper_messages.jsonl
[提示] 请重启 Cursor/VSCode 使补丁生效
```

### 步骤 3：修改 Y3 Helper 插件（添加 runLua 命令）

Claude 执行 `tools/install_y3helper_runlua.py`：

```bash
cd <项目路径>/tools
python install_y3helper_runlua.py
```

**预期输出**：
```
找到插件：C:\Users\xxx\.cursor\extensions\sumneko.y3-helper-x.x.x\dist\extension.js
已备份到：extension.js.backup
✓ runLua 命令安装成功！
请重启 VSCode/Cursor 使修改生效
```

### 步骤 4：配置游戏端代码

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

### 步骤 5：创建计划任务（可选，用于强制杀进程）

以管理员权限运行：

```bash
cd <项目路径>/tools
setup_kill_task.bat
```

这会创建计划任务，允许无 UAC 弹窗杀掉游戏进程。

### 步骤 6：重启编辑器

**必须完全关闭 Cursor/VSCode（包括所有进程），然后重新打开项目。**

### 步骤 7：验证安装

```bash
cd <项目路径>/tools

# 1. 启动游戏
python game_control.py launch

# 2. 等待加载
sleep 15

# 3. 检查状态
python game_control.py status
# 应显示: [OK] 游戏运行中 (PID: xxx)

# 4. 进入游戏
python game_control.py enter

# 5. 测试错误捕获
python game_control.py lua "print('[test] Hello!')"

# 6. 检查消息文件
tail "$TEMP/y3helper_messages.jsonl"
# 应看到 [test] Hello! 消息
```

---

## 📁 工具文件清单

```
<项目路径>/tools/
├── game_control.py              # 游戏控制主脚本
├── file_listener.py             # 消息文件监听器
├── error_sender.lua             # 游戏端错误发送模块
├── patch_y3helper_http.py       # 补丁1：print消息转发
├── patch_debugger_exception.py  # 补丁2：异常捕获
├── install_y3helper_runlua.py   # runLua命令安装
├── setup_kill_task.bat          # 计划任务安装
├── quick_enter.lua              # 快速进入游戏
├── restart_game.lua             # 重启游戏
└── temp/                        # 临时 Lua 脚本目录
```

---

## 🔄 插件更新后重新安装

Y3 Helper 插件更新后，需要重新执行所有补丁：

```bash
cd <项目路径>/tools

# 重新打补丁
python patch_y3helper_http.py
python patch_debugger_exception.py
python install_y3helper_runlua.py

# 重启编辑器
```

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

### 问题：消息文件没有内容
- 确认已打补丁并重启编辑器
- 检查补丁是否存在：`grep "FORWARD_TO_LISTENER" <extension.js路径>`
- 检查异常补丁：`grep "DEBUG_EXCEPTION_TRACKER" <extension.js路径>`

### 问题：异常没有被捕获
- 确认游戏是通过 Y3 Helper 启动的（带调试器）
- 确认 `patch_debugger_exception.py` 已执行
- 确认编辑器已重启

### 问题：游戏卡住无法操作
```bash
# 强制杀掉游戏进程
python game_control.py kill

# 或强制重启
python game_control.py frestart
```

---

## ✅ 安装完成确认清单

Claude 在安装完成后确认：

- [ ] Y3 Helper 插件已安装
- [ ] print 消息转发补丁已应用
- [ ] 调试器异常捕获补丁已应用
- [ ] runLua 命令已添加到插件
- [ ] debugs.lua 包含消息处理器
- [ ] 编辑器已重启
- [ ] 游戏能通过 `game_control.py launch` 启动
- [ ] 消息能正确写入 `%TEMP%\y3helper_messages.jsonl`
- [ ] 异常能被捕获到消息文件
