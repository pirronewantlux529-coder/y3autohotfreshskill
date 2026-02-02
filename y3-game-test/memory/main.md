# 游戏测试 - 核心记忆 (必读)

> ⚠️ **每次开始游戏测试工作前必须阅读此文件！**

## 🎮 游戏启动后必做步骤

游戏启动后**不会自动进入游戏**，必须手动执行进入命令获得角色：

```bash
cd "D:\Y3\ORPG项目总包\ORPG\maps\EntryMap\script\tools"

# 1. 游戏启动后，必须执行 enter 命令进入游戏
python game_control.py enter

# 2. 等待 8-10 秒让角色完全加载
sleep 8

# 3. 验证角色已获得
python game_control.py lua "local p = y3.player(1); print('[test] 玩家:', p, '角色:', p.mainhero)"
```

**不执行 enter 的后果**：
- ❌ `y3.player(1).mainhero` 返回 nil
- ❌ 所有依赖角色的测试都会失败
- ❌ 装备/技能/UI 测试全部无法进行

## 📋 标准测试启动流程

```bash
cd "D:\Y3\ORPG项目总包\ORPG\maps\EntryMap\script\tools"

# 完整流程
python file_listener.py &    # 1. 启动监听器（必须！）
python game_control.py launch # 2. 启动游戏
sleep 20                       # 3. 等待加载
python game_control.py enter   # 4. 进入游戏（获得角色）
sleep 8                        # 5. 等待角色加载
python game_control.py lua "print('[ready] 游戏就绪')"  # 6. 验证
```

## 🔄 快速重启流程

```bash
# 一键重启并进入
python game_control.py frestart

# frestart 会自动：杀进程 → 启动 → 等待 → 进入游戏
```

## ⚠️ 常见错误

### 错误1：角色为 nil
**现象**：`attempt to index a nil value (local 'hero')`
**原因**：没有执行 `enter` 命令
**解决**：`python game_control.py enter` 然后等待 8 秒

### 错误2：命令无响应
**现象**：lua 命令发送后没有任何输出
**原因**：游戏卡在异常断点
**解决**：
```bash
tail -20 "$TEMP/y3helper_messages.jsonl"  # 查看异常
python game_control.py c                   # 继续运行
```

### 错误3：监听器看不到输出
**现象**：执行命令成功但看不到 print 结果
**原因**：没有启动 file_listener.py
**解决**：重新启动 `python file_listener.py`

---
*最后更新：2025-01-27*
