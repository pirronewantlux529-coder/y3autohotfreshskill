# Y3 Helper 调试环境安装向导

本文档是 Claude Code 的交互式安装指南。Claude 会自动搜索路径、询问用户确认、并完成所有配置。

---

## 🤖 Claude 自动安装流程

当用户请求安装此 skill 时，Claude 应按以下流程执行：

### 第一步：自动探测环境

Claude 执行以下搜索来自动发现用户环境：

```python
import os
import glob

# 1. 搜索 Y3 编辑器安装路径
y3_patterns = [
    "C:/Y3", "D:/Y3", "E:/Y3",
    "C:/*/Y3", "D:/*/Y3",
    os.path.expanduser("~/Y3")
]
# 查找包含 games/2.0/game/Engine/Binaries/Win64/Game_x64h.exe 的目录

# 2. 搜索 Y3 项目路径（包含 main.lua 的 script 目录）
# 在 Y3 目录下搜索 **/maps/*/script/main.lua

# 3. 搜索编辑器插件路径
editor_patterns = [
    os.path.expanduser("~/.cursor/extensions/sumneko.y3-helper-*"),
    os.path.expanduser("~/.vscode/extensions/sumneko.y3-helper-*"),
    "C:/Users/*/.cursor/extensions/sumneko.y3-helper-*",
    "C:/Users/*/.vscode/extensions/sumneko.y3-helper-*"
]
```

### 第二步：向用户确认发现的路径

Claude 使用 AskUserQuestion 工具确认：

```
我找到了以下路径，请确认是否正确：

1. Y3 编辑器: D:\Y3\y3
2. 项目脚本目录: D:\Y3\MyProject\maps\MyMap\script
3. 编辑器插件: C:\Users\xxx\.cursor\extensions\sumneko.y3-helper-1.0.0

是否正确？如果不对请提供正确路径。
```

### 第三步：自动执行安装

确认后，Claude 自动执行以下操作：

---

## 📋 详细安装步骤

### 步骤 1：修改 Y3 Helper 插件（添加 runLua 命令）

**Claude 自动执行：**

```python
# 查找并修改 extension.js
ext_path = "<探测到的插件路径>/dist/extension.js"

# 读取文件
with open(ext_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已安装
if 'y3-helper.runLua' in content:
    print("runLua 已安装，跳过")
else:
    # 备份
    with open(ext_path + '.backup', 'w', encoding='utf-8') as f:
        f.write(content)

    # 修改
    old = 'a.commands.registerCommand("y3-helper.reloadLua",(async()=>{for(let e of g.allClients)e.notify("command",{data:".rd"})}))'
    new = old + ',a.commands.registerCommand("y3-helper.runLua",(async(code)=>{for(let e of g.allClients)e.notify("command",{data:code})}))'
    content = content.replace(old, new)

    with open(ext_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("runLua 命令已添加，请重启编辑器")
```

或运行安装脚本：
```bash
python <skill目录>/tools/install_y3helper_runlua.py
```

---

### 步骤 2：配置游戏端代码

**Claude 自动检查并修改：**

#### 2.1 检查 main.lua

```python
main_lua = "<项目路径>/main.lua"
# 检查是否包含 require 'base.debugs'
# 如果没有，提示用户添加：
"""
if debug.sethook then
    y3.config.debug = true
    require 'base.debugs'
end
"""
```

#### 2.2 修改 base/debugs.lua

Claude 检查 `<项目路径>/base/debugs.lua` 是否包含 Y3 Helper 消息处理器：

```lua
-- 检查是否包含这段代码
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

如果没有，从 `examples/debugs_y3helper_patch.lua` 复制代码添加到文件末尾。

---

### 步骤 3：复制工具脚本

**Claude 自动执行：**

```python
import shutil

skill_tools = "<skill目录>/tools"
project_tools = "<项目路径>/tools"

# 确保目录存在
os.makedirs(project_tools, exist_ok=True)

# 复制文件
files = ['game_control.py', 'quick_enter.lua', 'restart_game.lua', 'debug_template.lua']
for f in files:
    shutil.copy(f"{skill_tools}/{f}", f"{project_tools}/{f}")
```

---

### 步骤 4：创建启动脚本 launch_game.bat

**Claude 自动生成（根据探测到的路径）：**

```python
# 获取关卡ID（从项目配置中读取，或询问用户）
level_id = "<从项目中读取或询问用户>"

bat_content = f'''@echo off
chcp 65001 >nul
cd /d "{y3_dir}\\games\\2.0\\game\\Engine\\Binaries\\Win64"
start "" "Game_x64h.exe" --dx11 --start=Python "--python-args=type@editor_game,subtype@editor_game,editor_map_path@{project_path},level_id@{level_id},release@true,lua_dummy@space,lua_wait_debugger@true" --plugin-config=Plugins-PyQt --console --luaconsole
'''

with open(f"{project_tools}/launch_game.bat", 'w', encoding='utf-8') as f:
    f.write(bat_content)
```

**关于关卡ID：**
- Claude 可以搜索项目中的 `.json` 或配置文件查找 level_id
- 或者询问用户提供
- 常见位置：项目根目录的配置文件，或 Y3 编辑器中查看

---

### 步骤 5：创建计划任务（无UAC启动）

**Claude 自动执行（会弹出一次管理员确认）：**

```python
import subprocess

bat_path = f"{project_tools}/launch_game.bat"
cmd = f'''powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'schtasks /create /tn Y3LaunchGame /tr \"{bat_path}\" /sc once /st 00:00 /rl highest /f & echo 创建成功 & pause' -Verb RunAs -Wait"'''

subprocess.run(cmd, shell=True)
```

---

### 步骤 6：验证安装

**Claude 自动测试：**

```bash
cd <项目路径>/tools
python game_control.py launch   # 测试启动游戏（应无UAC弹窗）
# 等待游戏加载...
python game_control.py test     # 测试发送命令
```

检查日志确认：
```bash
grep "Hello from game_control" <项目路径>/.log/lua_player01.log
```

---

## 🔍 路径搜索参考

### Y3 编辑器路径特征
- 包含 `games/2.0/game/Engine/Binaries/Win64/Game_x64h.exe`
- 常见位置：`D:\Y3\y3`, `C:\Y3\y3`

### Y3 项目路径特征
- 包含 `main.lua`
- 目录结构：`<项目>/maps/<地图名>/script/main.lua`
- 包含 `y3/` 框架目录
- 包含 `base/` 目录

### 关卡ID获取方法
- 在 Y3 编辑器中打开项目，查看关卡属性
- 搜索项目中的 `level_id` 或 `switch_level`
- 查看 `tools/restart_game.lua` 中是否已有配置

---

## ⚠️ WSL 特殊配置

如果用户使用 WSL：
- 必须使用 Windows Python：`/mnt/c/Windows/py.exe`
- 路径转换：`D:\Y3\...` → `/mnt/d/Y3/...`

---

## 🐛 故障排除

| 问题 | 原因 | Claude 解决方案 |
|------|------|----------------|
| runLua not found | 插件未修改 | 重新运行 install_y3helper_runlua.py |
| 连接被拒绝 | 编辑器未运行 | 提示用户打开 Cursor/VSCode |
| 游戏收不到命令 | debugs.lua 未配置 | 检查并添加消息处理器代码 |
| 中文路径乱码 | bat编码问题 | 确保 bat 文件包含 `chcp 65001` |
| UAC弹窗 | 计划任务未创建 | 重新创建计划任务 |

---

## ✅ 安装完成确认清单

Claude 完成安装后应确认：

- [ ] Y3 Helper 插件已修改（runLua 命令）
- [ ] 编辑器已重启
- [ ] debugs.lua 包含消息处理器
- [ ] 工具脚本已复制
- [ ] launch_game.bat 已生成（路径正确）
- [ ] 计划任务已创建
- [ ] `python game_control.py launch` 测试通过
- [ ] `python game_control.py test` 测试通过
