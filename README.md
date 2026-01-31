# Y3 Game Test Skill

Y3 ORPG 游戏热更新与测试工具。通过计划任务实现**无UAC弹窗**启动游戏，支持热更新和远程执行 Lua 代码。

## 功能

- 🚀 **启动游戏** - 通过计划任务启动，无UAC弹窗
- 🔄 **热更新** - 实时更新 Lua 代码无需重启
- 📝 **执行 Lua** - 远程执行任意 Lua 代码
- 🔧 **调试工具** - 内置调试脚本模板

## 安装

### 方法 1：让 Claude Code 自动安装（推荐）

1. **克隆仓库到项目 skills 目录：**

```bash
cd <你的Y3项目>/maps/<地图>/script/.claude/skills
git clone https://github.com/pirronewantlux529-coder/y3autohotfreshskill.git y3-game-test
```

2. **让 Claude Code 完成配置：**

直接告诉 Claude Code：

```
请阅读 .claude/skills/y3-game-test/Y3_HELPER_SETUP.md 并帮我完成安装配置
```

Claude 会自动：
- 搜索并确认 Y3 编辑器路径、项目路径
- 修改 Y3 Helper 插件（添加 runLua 命令）
- 检查并配置 main.lua 和 debugs.lua
- 复制工具脚本
- 生成 launch_game.bat
- 创建计划任务（无UAC启动）
- 验证安装

### 方法 2：手动安装

参见 [Y3_HELPER_SETUP.md](Y3_HELPER_SETUP.md) 的详细步骤。

## 使用

### 命令行

```bash
# 启动游戏（无UAC弹窗）
python game_control.py launch

# 启动游戏（通过Y3 Helper，会弹UAC）
python game_control.py launch2

# 热更新
python game_control.py reload

# 快速进入游戏
python game_control.py enter

# 重启游戏
python game_control.py restart

# 执行 Lua 代码
python game_control.py lua "print('Hello!')"

# 执行测试脚本
python game_control.py run debug_template

# 简单打印测试
python game_control.py test

# 启动错误监听器（新窗口）
python game_control.py listen

# 在游戏中启用错误发送
python game_control.py errors
```

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
├── Y3_HELPER_SETUP.md          # 安装配置指南（Claude 自动安装用）
├── README.md                   # 本文件
├── tools/
│   ├── game_control.py         # 游戏控制脚本
│   ├── install_y3helper_runlua.py  # 插件安装脚本
│   ├── launch_game.bat.template    # 启动脚本模板
│   ├── quick_enter.lua         # 快速进入游戏
│   ├── restart_game.lua        # 重启游戏
│   └── debug_template.lua      # 调试模板
└── examples/
    ├── debugs_y3helper_patch.lua   # debugs.lua 补丁
    ├── y3helper_client.py          # Python 客户端库
    └── example_test.py             # 使用示例
```

## 前提条件

- Cursor 或 VSCode
- Y3 Helper 插件 (sumneko.y3-helper)
- Python 3.x

## 注意事项

1. **必须先启动编辑器** - Y3 Helper 在编辑器中运行
2. **不要直接启动游戏 exe** - 会闪退，必须通过计划任务或 Y3 Helper
3. **WSL 用户** - 需要使用 Windows Python (`/mnt/c/Windows/py.exe`)
4. **中文路径** - launch_game.bat 需要包含 `chcp 65001` 解决乱码

## 更新

```bash
cd <你的Y3项目>/maps/<地图>/script/.claude/skills/y3-game-test
git pull
```

Y3 Helper 插件更新后需要重新运行 `install_y3helper_runlua.py`。

## License

MIT
