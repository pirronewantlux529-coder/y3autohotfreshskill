# Y3 Game Test Skill

> by Y3海豹

Y3（英雄三国，KK对战平台游戏）游戏热更新与测试调试工具。通过计划任务实现**无UAC弹窗**启动游戏，支持热更新和远程执行 Lua 代码。

**🎯 支持无人值守自动对某个模块进行不断的调试优化迭代！**

## 🎬 效果演示

<p align="center">
  <img src="game_control_demo1.gif" alt="游戏控制演示1" width="480">
  <img src="game_control_demo2.gif" alt="游戏控制演示2" width="480">
</p>

## 适用人群

- 🚀 Y3 地图编辑器 Lua 作者

## 核心功能

- 🚀 **启动/关闭/重启/暂停游戏** - 通过计划任务启动，无UAC弹窗
- 🔄 **热更新** - 实时更新 Lua 代码无需重启，随时修改代码并应用
- 📝 **执行 Lua** - 远程执行任意 Lua 代码，支持自动打断点分析
- ✅ **自动错误检测** - `lua_executor.py` 发送代码后自动检查日志错误和异常
- 🔧 **调试工具** - 内置调试脚本模板和测试示例
- 🔍 **异常捕获** - 自动捕获引擎级异常，写入消息文件供监听
- 💓 **心跳监控** - 长时间运行时自动检测卡死并恢复

## 💡 使用建议

想要完美使用，需要你不断迭代更新自己的 tools。这里仅提供一些案例，主要是方便控制的热更新代码，比如：
- 在选择界面帮你自动选角色
- 自动刷兵
- 刷全部技能测伤害和 bug

## 安装

### 方法 1：让 Claude Code 自动安装（推荐）

1. **克隆仓库到项目 skills 目录：**

```bash
cd <你的Y3项目>/maps/<地图>/script/.claude/skills
git clone https://github.com/pirronewantlux529-coder/y3autohotfreshskill.git y3-game-test
```

2. **复制 tools 目录到项目 script 目录：**

```bash
cp -r y3-game-test/tools ../../tools
```

3. **配置 memory 记忆文件（重要！）：**

```bash
cd y3-game-test/memory
```

> ⚠️ **memory/ 目录内的文件是示例，必须根据你的项目路径修改！**
>
> 打开 `memory/main.md` 等文件，将里面的路径改成你的实际项目路径。
> 这些记忆文件帮助 Claude 记住测试经验和避坑指南。

4. **让 Claude Code 完成配置：**

直接告诉 Claude Code：

```
请阅读 .claude/skills/y3-game-test/Y3_HELPER_SETUP.md 并帮我完成安装配置
```

Claude 会自动：

- 修改 Y3 Helper 插件（添加 runLua 命令）
- 检查并配置 main.lua 和 debugs.lua
- 创建计划任务（无UAC启动）
- 验证安装

5. **⚠️ 重要：将 skill 信息添加到项目 CLAUDE.md**

在你的项目 `CLAUDE.md` 文件的 Skills 部分添加：

```markdown
## 🎯 项目Skills（必读！）

| 任务类型 | Skill位置 | 说明 |
|---------|----------|------|
| **游戏测试** | `.claude/skills/y3-game-test/SKILL.md` | 热更新、重启游戏、执行测试脚本、心跳监控 |

### ⚠️ 强制要求
- **测试游戏** → 必须先读 `y3-game-test/SKILL.md`
```

这样 Claude 才会在测试时自动查阅这个 skill。

### 🎉 自动配置（无需手动设置路径！）

**所有路径自动从项目文件检测，无需手动配置：**

| 配置项 | 自动读取位置 |
|--------|-------------|
| 游戏可执行文件 | `.vscode/settings.json` → `Y3-Helper.EditorPath` |
| 关卡 ID | `header.project` → `entry_map.id` |
| 项目路径 | 从 `tools` 目录位置自动推断 |

**验证配置：**
```bash
cd <项目>/script/tools
python game_control.py config
```

### 方法 2：手动安装

参见 [Y3_HELPER_SETUP.md](Y3_HELPER_SETUP.md) 的详细步骤。

## 使用

### 命令行（基础）

```bash
# 启动游戏（无UAC弹窗）
python game_control.py launch

# 快速进入游戏
python game_control.py enter

# 强制杀游戏进程
python game_control.py kill

# 强制重启（杀进程 → 启动 → 进入游戏）
python game_control.py frestart
```

### 推荐用法：lua_executor（自动检测错误）

```bash
# 执行Lua代码（自动检测错误）
python lua_executor.py "print('test')"

# 执行测试脚本（自动检测错误）
python lua_executor.py --file pet_test
```

**Python脚本中使用**：
```python
from lua_executor import execute_lua, print_result

result = execute_lua("your_code")
print_result(result)

if not result.success:
    print('失败:', result.error)
    exit(1)
```

### 旧方式：game_control.py

```bash
# 执行 Lua 代码（带确认，但不自动检查错误）
python game_control.py lua "print('Hello!')"

# 执行测试脚本
python game_control.py run debug_template
```

### 监控系统

**短期测试（推荐）**：
```bash
# 使用 lua_executor，每次执行自动检测错误
python lua_executor.py "your_code"
```

**长时间运行（如压力测试）**：
```bash
# 启动游戏
python game_control.py launch && sleep 20
python lua_executor.py --file quick_enter && sleep 8

# 启动心跳监控器（前台实时显示）
python heartbeat_monitor.py --interval 10

# 或后台运行
python heartbeat_monitor.py --interval 10 > monitor.log 2>&1 &
tail -f monitor.log
```

**监控器功能对比**：

| 工具 | 用途 | 使用场景 |
|------|------|---------|
| `lua_executor.py` | 执行Lua并自动检测错误 | 日常开发测试 |
| `heartbeat_monitor.py` | 心跳检测，自动恢复卡死 | 长时间无人值守运行 |
| `file_listener.py` | 实时显示游戏消息 | 查看实时输出（可选） |

> **首次使用前必须创建计划任务**（以管理员身份运行）：
> - `setup_launch_task.bat` - 创建启动游戏任务（无UAC弹窗启动）
> - `setup_kill_task.bat` - 创建杀进程任务（强制杀游戏进程）
>
> 不创建也能用，但会弹UAC确认框。

### Claude Code

安装完成后，直接告诉 Claude：

```
启动游戏
热更新代码
执行测试脚本 xxx
```

Claude 会自动调用相关命令。

## 文件结构

```
y3-game-test/
├── SKILL.md                    # Skill 使用说明（Claude 读取）
├── README_NEW_WORKFLOW.md      # v3.0 新工作流程详解
├── RELEASE_NOTES.md            # 版本更新说明
├── Y3_HELPER_SETUP.md          # 安装配置指南
├── README.md                   # 本文件
├── memory/                     # ⚠️ 记忆文件（需根据项目路径修改！）
│   ├── main.md                 # 主要测试经验（必读）
│   └── ...                     # 其他记忆文件
├── tools/                      # 核心工具集
│   ├── lua_executor.py         # ⭐ 自动错误检测执行器（v3.0新增）
│   ├── test_with_executor.py   # ⭐ 使用示例和测试模板（v3.0新增）
│   ├── heartbeat_monitor.py    # ⭐ 心跳监控器（v3.0优化）
│   ├── game_control.py         # 游戏控制脚本
│   ├── file_listener.py        # 消息文件监听器
│   ├── install_y3helper_runlua.py  # 插件安装脚本
│   ├── quick_enter.lua         # 快速进入游戏
│   └── restart_game.lua        # 重启游戏
└── examples/
    ├── debugs_y3helper_patch.lua   # debugs.lua 补丁
    └── y3helper_client.py          # Python 客户端库
```

## 前提条件

- Cursor 或 VSCode
- **Y3 Helper 插件 (Y3小助手)** - 必须安装，否则无法使用。请自行查询 Y3 Helper 的安装方法
- Python 3.x

## ⚠️ 注意事项

1. **必须安装 Y3 Helper 插件** - 核心功能需要对 Y3 Helper 打补丁，插件更新后需重新打补丁
2. **必须先启动 VSCode/Cursor** - Y3 Helper 插件在代码编辑器中运行（不是游戏编辑器）
3. **不要直接启动游戏 exe** - 会闪退，必须通过计划任务或 Y3 Helper

## 更新

```bash
cd <你的Y3项目>/maps/<地图>/script/.claude/skills/y3-game-test
git pull
```

Y3 Helper 插件更新后需要重新运行 `install_y3helper_runlua.py`。

## License

MIT
