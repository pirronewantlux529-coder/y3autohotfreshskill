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
例如: D:\Y3\MyProject\maps\MyMap\script

请输入路径：
```

### 问题 3：运行环境
```
你使用的是什么终端环境？
1. Windows CMD/PowerShell（推荐）
2. WSL (Windows Subsystem for Linux)
```

---

## 📋 安装步骤

### 步骤 1：检查 Y3 Helper 插件是否已安装

在 Cursor/VSCode 中按 `Ctrl+Shift+X` 打开扩展市场，搜索 `Y3 Helper`。

**如果未安装**：
1. 搜索 "Y3 Helper"
2. 安装 `sumneko.y3-helper`
3. 重启编辑器

---

### 步骤 2：修改 Y3 Helper 插件（添加 runLua 命令）⚠️ 重要

Y3 Helper 默认只有 `reloadLua` 命令，我们需要添加 `runLua` 命令来执行任意 Lua 代码。

#### 方法 A：运行安装脚本（推荐）

```bash
# Windows
cd <项目路径>/tools
python install_y3helper_runlua.py

# WSL
/mnt/c/Windows/py.exe install_y3helper_runlua.py
```

#### 方法 B：手动修改

1. **找到插件文件**：
   - Cursor: `C:\Users\<用户名>\.cursor\extensions\sumneko.y3-helper-x.x.x\dist\extension.js`
   - VSCode: `C:\Users\<用户名>\.vscode\extensions\sumneko.y3-helper-x.x.x\dist\extension.js`

2. **备份文件**（重要！）：
   ```
   复制 extension.js 为 extension.js.backup
   ```

3. **编辑 extension.js**，搜索这段代码：
   ```javascript
   a.commands.registerCommand("y3-helper.reloadLua",(async()=>{for(let e of g.allClients)e.notify("command",{data:".rd"})}))
   ```

4. **在这段代码后面添加**（注意开头的逗号）：
   ```javascript
   ,a.commands.registerCommand("y3-helper.runLua",(async(code)=>{for(let e of g.allClients)e.notify("command",{data:code})}))
   ```

5. **保存文件，重启编辑器**

#### 验证修改成功

重启编辑器后，按 `Ctrl+Shift+P`，输入 `y3`，应该能看到：
- `Y3 Helper: Reload Lua` （原有）
- `Y3 Helper: Run Lua` （新增）

---

### 步骤 3：配置游戏端代码（修改 debugs.lua）⚠️ 重要

游戏端需要注册消息处理器，才能接收 Y3 Helper 发来的命令。

#### 3.1 确认 main.lua 加载 debugs.lua

检查 `main.lua` 是否包含：
```lua
if debug.sethook then     --是本地开发环境
    y3.config.debug = true
    require 'base.debugs' --debug功能开启
end
```

如果没有，添加到 `main.lua` 的初始化部分。

#### 3.2 修改 base/debugs.lua

在 `base/debugs.lua` 中添加以下代码：

```lua
---重载lua文件
---@param name string lua文件名
---@return table|nil|any 重载代码
function _reloadlua(name)
    package.loaded[name]=nil
    return require (name)
end

print('---------------当前为本地环境，可进行调试----------------------')

-- F5 热更新快捷键
y3.game:event('键盘-按下', y3.const.KeyboardKey['F5'], function ()
    print('-----------------热调试内容------------------------')
    _reloadlua('base.hotfresh')
    print('-----------------热调试内容结束------------------------')
end)

-- ⚠️ 关键代码：Y3 Helper 消息处理器
-- 确保 Y3 Helper 的 command 处理器正确注册
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

**关键说明**：
- `_reloadlua` 函数用于热更新模块
- `y3.develop.helper.registerMethod('command', ...)` 注册消息处理器
- `y3.develop.console.input(params.data)` 执行收到的 Lua 代码

---

### 步骤 4：复制工具脚本

将以下文件复制到你的项目 `tools/` 目录：

```
从 skill 目录复制:
  tools/game_control.py        → <项目>/tools/game_control.py
  tools/quick_enter.lua        → <项目>/tools/quick_enter.lua
  tools/restart_game.lua       → <项目>/tools/restart_game.lua
  tools/debug_template.lua     → <项目>/tools/debug_template.lua
```

**注意**：`restart_game.lua` 中的 `level_id` 需要改成你的关卡 ID。

---

### 步骤 5：设置管理员权限（避免每次启动弹窗）

游戏 exe 需要管理员权限运行。设置自动提权后，启动游戏时不会再弹出确认窗口。

#### 方法 A：Claude 自动设置（推荐）

让 Claude 执行以下 PowerShell 命令：

```powershell
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers' -Name '<游戏exe路径>' -Value 'RUNASADMIN' -Type String -Force
```

例如：
```powershell
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers' -Name 'd:\Y3\y3\games\2.0\game\Engine\Binaries\Win64\Game_x64h.exe' -Value 'RUNASADMIN' -Type String -Force
```

#### 方法 B：手动设置

1. 找到游戏 exe 文件（通常在 `Y3安装目录\games\2.0\game\Engine\Binaries\Win64\Game_x64h.exe`）
2. 右键点击 → **属性**
3. 切换到 **兼容性** 选项卡
4. 勾选 **以管理员身份运行此程序**
5. 点击 **确定**

---

### 步骤 6：验证安装

1. **启动编辑器**（Cursor/VSCode）并打开项目
2. **启动游戏**：
   ```bash
   cd <项目路径>/tools
   python game_control.py launch
   ```
3. **等待游戏加载完成，运行测试命令**：
   ```bash
   python game_control.py test
   ```
4. **检查游戏日志**：
   ```bash
   grep "Hello from game_control" .log/lua_player01.log
   ```

如果看到输出，说明安装成功！

---

## ⚠️ WSL 特殊配置

如果使用 WSL 环境：

1. **必须以管理员权限运行 WSL**
2. **必须使用 Windows Python**：
   ```bash
   # 正确 ✓
   /mnt/c/Windows/py.exe game_control.py test

   # 错误 ✗（无法连接 Windows 端口）
   python game_control.py test
   ```

---

## 🔄 插件更新后重新安装

Y3 Helper 插件更新后，`runLua` 命令会丢失，需要重新执行步骤 2：

```bash
python tools/install_y3helper_runlua.py
# 然后重启编辑器
```

---

## 🐛 故障排除

### 问题：command 'y3-helper.runLua' not found
**原因**：插件未修改或编辑器未重启
**解决**：
1. 运行 `install_y3helper_runlua.py`
2. 重启编辑器

### 问题：连接被拒绝
**原因**：编辑器未运行或 Y3 Helper 未启动
**解决**：
1. 打开 Cursor/VSCode
2. 打开 Y3 项目
3. 查看编辑器底部状态栏是否显示 Y3 Helper

### 问题：游戏收不到命令
**原因**：`debugs.lua` 未正确配置
**解决**：
1. 检查 `main.lua` 是否加载 `debugs.lua`
2. 检查 `debugs.lua` 是否包含消息处理器代码
3. 重启游戏（通过 Y3 Helper 启动）
4. 查看日志是否有 `[debugs] Y3 Helper command 处理器已注册`

### 问题：端口文件不存在
**原因**：游戏未启动
**解决**：`log/helper_port.lua` 在游戏启动后自动生成，先启动游戏

---

## ✅ 安装完成确认清单

- [ ] Y3 Helper 插件已安装
- [ ] `extension.js` 已添加 `runLua` 命令
- [ ] 编辑器已重启
- [ ] `main.lua` 加载 `debugs.lua`
- [ ] `debugs.lua` 包含消息处理器代码
- [ ] 工具脚本已复制到 `tools/` 目录
- [ ] 游戏 exe 已设置管理员权限（不弹窗）
- [ ] `python game_control.py launch` 能启动游戏
- [ ] `python game_control.py test` 测试通过
