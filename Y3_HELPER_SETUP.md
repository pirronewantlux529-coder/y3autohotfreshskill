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
示例: D:\Y3\你的项目\maps\地图名\script

请输入你的项目脚本路径：
```

---

## 📋 安装步骤

### 步骤 0：复制 tools 目录到项目（重要！）

**tools 目录必须放在项目的 script 目录下，不能放在其他位置！**

#### 正确的目录结构

```
你的Y3项目/                        # 项目根目录（包含 header.project）
├── header.project                 # 项目配置文件
├── maps/
│   └── 你的地图名/
│       └── script/                # 脚本目录（包含 main.lua）
│           ├── main.lua           # 游戏入口
│           ├── .vscode/           # VSCode/Cursor 配置（Y3 Helper 自动创建）
│           │   └── settings.json  # 包含 Y3-Helper.EditorPath
│           ├── tools/             # ⭐ tools 必须在这里！
│           │   ├── config.py
│           │   ├── game_control.py
│           │   └── ...
│           └── ...
```

#### 复制方法

**方法 1：命令行复制**
```bash
# 假设你已克隆仓库到 .claude/skills/y3-game-test
cd <你的项目>/maps/<地图名>/script
cp -r .claude/skills/y3-game-test/tools ./tools
```

**方法 2：手动复制**
1. 打开仓库目录，找到 `tools` 文件夹
2. 复制整个 `tools` 文件夹
3. 粘贴到你项目的 `script` 目录下

> ⚠️ **关键检查**：复制后，`tools` 目录和 `main.lua` 应该在同一层级！

### 步骤 1：验证配置检测

运行配置检测脚本，确认路径都能正确识别：

```bash
cd <项目路径>/script/tools
python config.py
```

**预期输出**（所有项目应显示 [OK]）：
```
==================================================
Y3 游戏控制工具 - 自动检测配置
==================================================

[OK] 脚本路径: D:\...\script
[OK] 项目路径: D:\...\项目名
[OK] 关卡 ID: xxx-xxx-xxx
[OK] 编辑器路径: d:\Y3\y3\games\2.0\game\Editor.exe
[OK] 游戏可执行文件: d:\Y3\y3\games\2.0\game\Engine\Binaries\Win64\Game_x64h.exe

[OK] 所有配置检测成功!
```

**如果显示 [!!] 错误**：

**方法 1：使用搜索功能（推荐）**

如果 tools 没有放在正确位置，可以用搜索功能自动找到你的项目：

```bash
python config.py --search D:\Y3
# 或搜索你存放 Y3 项目的目录
python config.py --search C:\Users\你的用户名\Documents
```

程序会列出找到的所有 Y3 项目，选择一个后会自动保存配置。

**方法 2：手动排查**
- `脚本路径` 错误 → 确认 tools 目录在正确位置（`<项目>/maps/<地图>/script/tools/`）
- `编辑器路径` 错误 → 在 VSCode/Cursor 中打开项目，Y3 Helper 会自动写入配置
- `关卡 ID` 错误 → 确认项目根目录有 `header.project` 文件

**清除保存的配置**：
```bash
python config.py --clear
```

### 步骤 2：检查 Y3 Helper 插件

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

### 步骤 3：创建项目 CLAUDE.md（重要！）

检查 script 目录下是否存在 `CLAUDE.md`。

**如果已存在，跳过此步骤。**

如果不存在则需要创建：

**Claude 执行：**

1. 扫描 script 目录结构，了解项目架构
2. 创建 `CLAUDE.md` 文件，包含以下核心内容：

```markdown
# Y3 项目开发指南 - Claude 专用

## 🔥 核心原则（必读！）

### API 验证铁律

**⚠️ 禁止凭想象编写 API！任何不确定的 API 都必须先搜索验证！**

1. **每个函数都要搜索验证**
   ```bash
   rg "function_name" --type lua
   rg ":method_name" --type lua
   ```

2. **找不到定义 = 不能使用**
   - 在 y3/ 框架中找到定义
   - 或在现有代码中找到正确用法
   - 确认参数顺序和调用方式

3. **常见错误示例**
   ```lua
   -- ❌ 错误：凭想象使用
   player:create_unit(...)

   -- ✅ 正确：搜索后发现真实API
   y3.unit.create_unit(player, ...)
   ```

## 📁 目录结构

- `y3/` - Y3框架（只读，不可修改）
- `base/` - 基础库（可修改）
- `mapwork/` - 地图逻辑（可修改）
- `tables/` - 配置数据（只读，自动生成）

## 🔧 开发规范

1. 所有变量使用 `local` 声明
2. 修改前先搜索现有实现
3. 优先复用现有代码，避免重复造轮子
```

**为什么需要这个文件：**
- 防止 Claude 凭想象编写不存在的 API
- 确保每次调用都有据可查
- 新手上手更快更准确

### 步骤 4：安装 Y3 Helper 补丁（错误捕获）

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

### 步骤 5：修改 Y3 Helper 插件（添加 runLua 命令）

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

### 步骤 6：配置游戏端代码

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

### 步骤 7：创建计划任务（推荐，无UAC弹窗）

#### 6.1 生成启动脚本

先运行自动生成脚本，它会读取项目配置并生成 `launch_game.bat`：

```bash
cd <项目路径>/tools
python generate_launch_bat.py
```

**预期输出**：
```
[OK] launch_game.bat 已生成！
  路径: ...\tools\launch_game.bat
  游戏目录: d:\Y3\y3\games\2.0\game\Engine\Binaries\Win64
  项目路径: d:\Y3\你的项目路径
  关卡 ID: xxx-xxx-xxx
```

#### 6.2 创建计划任务

以管理员权限运行以下脚本：

```bash
# 右键点击 → "以管理员身份运行"

# 1. 创建启动游戏的计划任务
setup_launch_task.bat

# 2. 创建杀进程的计划任务
setup_kill_task.bat
```

**创建后的效果**：
- `Y3LaunchGame` 任务 → `python game_control.py launch` 无UAC弹窗启动游戏
- `Y3KillGame` 任务 → `python game_control.py kill` 无UAC弹窗杀进程

**不创建计划任务也能使用**，但每次会弹出UAC确认框。

> ⚠️ **必须以管理员身份运行 bat 文件**：右键点击 → "以管理员身份运行"

### 步骤 8：重启编辑器

**必须完全关闭 Cursor/VSCode（包括所有进程），然后重新打开项目。**

### 步骤 9：验证安装

```bash
cd <项目路径>/script/tools

# 1. 验证配置
python game_control.py config

# 2. 启动监听器（新开一个终端窗口）
python file_listener.py

# 3. 启动游戏（在原终端）
python game_control.py launch

# 4. 等待加载（约15-30秒）

# 5. 检查状态
python game_control.py status
# 应显示: [游戏] 运行中 - 游戏运行中 (PID: xxx)

# 6. 进入游戏
python game_control.py enter

# 7. 等待进入（约8秒）

# 8. 测试错误捕获
python game_control.py lua "print('[test] Hello!')"
# 监听器窗口应显示 [test] Hello! 消息
```

---

## 📁 工具文件清单

```
<项目路径>/tools/
├── game_control.py              # 游戏控制主脚本
├── config.py                    # 配置自动检测（无需手动配置）
├── generate_launch_bat.py       # 自动生成 launch_game.bat
├── file_listener.py             # 消息文件监听器
├── error_sender.lua             # 游戏端错误发送模块
├── patch_y3helper_http.py       # 补丁1：print消息转发
├── patch_debugger_exception.py  # 补丁2：异常捕获
├── install_y3helper_runlua.py   # runLua命令安装
├── setup_launch_task.bat        # 创建启动游戏计划任务
├── setup_kill_task.bat          # 创建杀进程计划任务
├── kill_game.ps1                # 杀进程脚本（计划任务调用）
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
