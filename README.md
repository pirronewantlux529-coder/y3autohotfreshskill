# Y3 Game Test Skill

Y3 ORPG 游戏热更新与测试工具。通过 Y3 Helper 插件实现游戏启动、热更新和远程执行 Lua 代码。

## 功能

- 🚀 **启动游戏** - 通过 Y3 Helper 启动游戏（避免命令行启动闪退）
- 🔄 **热更新** - 实时更新 Lua 代码无需重启
- 📝 **执行 Lua** - 远程执行任意 Lua 代码
- 🔧 **调试工具** - 内置调试脚本模板

## 安装

### 1. 复制 Skill 到项目

将此目录复制到你的 Y3 项目：
```
<你的项目>/maps/<地图>/script/.claude/skills/y3-game-test/
```

### 2. 运行安装向导

让 Claude Code 阅读 `Y3_HELPER_SETUP.md` 并按照提示完成安装。

或者手动执行：
```bash
cd tools
python install_y3helper_runlua.py
```

### 3. 复制工具脚本到项目

将 `tools/` 目录下的文件复制到你的项目 `tools/` 目录：
```bash
cp tools/*.py <你的项目>/maps/<地图>/script/tools/
cp tools/*.lua <你的项目>/maps/<地图>/script/tools/
```

### 4. 配置游戏端

确保 `base/debugs.lua` 包含 Y3 Helper 消息处理器（参见 `examples/debugs_y3helper_patch.lua`）

## 使用

### 命令行

```bash
# 启动游戏
python game_control.py launch

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
```

### Claude Code

让 Claude Code 使用此 skill：
```
请帮我测试游戏功能
```

Claude 会自动调用相关命令。

## 文件结构

```
y3-game-test/
├── SKILL.md              # Skill 使用说明
├── Y3_HELPER_SETUP.md    # 安装配置指南
├── README.md             # 本文件
├── tools/
│   ├── game_control.py   # 游戏控制脚本
│   ├── install_y3helper_runlua.py  # 插件安装脚本
│   ├── quick_enter.lua   # 快速进入游戏
│   ├── restart_game.lua  # 重启游戏
│   └── debug_template.lua # 调试模板
└── examples/
    ├── debugs_y3helper_patch.lua  # debugs.lua 补丁
    ├── y3helper_client.py         # Python 客户端库
    └── example_test.py            # 使用示例
```

## 前提条件

- Cursor 或 VSCode
- Y3 Helper 插件 (sumneko.y3-helper)
- Python 3.x

## 注意事项

1. **必须先启动编辑器** - Y3 Helper 在编辑器中运行
2. **不要直接启动游戏 exe** - 会闪退，必须通过 Y3 Helper
3. **WSL 用户** - 需要使用 Windows Python (`/mnt/c/Windows/py.exe`)

## License

MIT
