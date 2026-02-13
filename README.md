# Y3 Game Test Skill

> by Y3海豹

Y3 游戏热更新与自动化测试工具，专为 **Claude Code** 打造。启动游戏、热更新、执行 Lua、截图验证，全部命令行搞定，支持无人值守自动调试迭代。

## 🎬 效果演示

<p align="center">
  <img src="game_control_demo1.gif" alt="游戏控制演示1" width="480">
  <img src="game_control_demo2.gif" alt="游戏控制演示2" width="480">
</p>

## 核心功能

| 功能 | 说明 |
|------|------|
| 🚀 启动/重启/关闭游戏 | 通过计划任务启动，无 UAC 弹窗 |
| 🔄 热更新 | 实时更新 Lua 代码无需重启 |
| 📝 远程执行 Lua | 执行任意代码或 tools/ 下的脚本 |
| ✅ 自动错误检测 | 发送代码后自动检查日志错误和异常 |
| 📸 游戏截图 | 截取 DirectX 渲染画面，AI 可直接分析 UI 效果 |
| 💓 心跳监控 | 长时间运行自动检测卡死并恢复 |
| 🐕 Game Watchdog | 后台持久监控，自动恢复崩溃/卡死，失败时通知 Claude |

## 安装

### 前提

- **Cursor** 或 **VSCode**（必须安装 [Y3 Helper 插件](https://marketplace.visualstudio.com/items?itemName=sumneko.y3-helper)）
- **Python 3.x**

### 快速安装

```bash
# 1. 克隆到项目 skills 目录
cd <你的Y3项目>/maps/<地图>/script/.claude/skills
git clone https://github.com/pirronewantlux529-coder/y3autohotfreshskill.git y3-game-test

# 2. 复制 tools 到 script 目录
cp -r y3-game-test/tools ../../tools
```

然后告诉 Claude Code：

```
请阅读 .claude/skills/y3-game-test/Y3_HELPER_SETUP.md 并帮我完成安装配置
```

Claude 会自动完成剩余配置（打补丁、创建计划任务、验证安装）。

> 详细手动安装步骤见 [Y3_HELPER_SETUP.md](Y3_HELPER_SETUP.md)

## 使用

```bash
cd <项目路径>/script/tools

python game_control.py launch     # 启动游戏（无UAC弹窗）
python game_control.py enter      # 快速进入游戏
python game_control.py frestart   # 强制重启
python game_control.py kill       # 强制杀进程
python game_control.py ss         # 截取游戏画面
python game_control.py run <脚本> # 执行 tools/ 下的 lua 脚本
python game_control.py lua "代码" # 执行任意 Lua 代码
```

配合 Claude Code 使用时，直接用自然语言描述需求即可，无需记命令。

> 完整命令列表和 API 详见 [SKILL.md](SKILL.md)

## 更新

```bash
cd <你的Y3项目>/maps/<地图>/script/.claude/skills/y3-game-test
git pull
```

Y3 Helper 插件更新后需重新运行 `python install_y3helper_runlua.py`。

## License

MIT
