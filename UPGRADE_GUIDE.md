# y3-game-test v3.0 升级指南

## 🎯 升级理由

v3.0带来了**自动错误检测**功能，彻底解决"发了bug不知道"的问题：

- ✅ 每次执行Lua后自动检查日志错误和异常
- ✅ 结构化的成功/失败反馈
- ✅ 卡死时自动尝试恢复
- ✅ 无需手动查日志

## 📦 升级方法

### 方法1：Git拉取（推荐）

如果你的skill是通过git克隆的：

```bash
cd <项目路径>/.claude/skills/y3-game-test
git pull origin main

# 同步tools到项目
cp -r tools/* ../../tools/
```

### 方法2：手动下载

1. **备份旧版本**：
```bash
cd <项目路径>/.claude/skills
mv y3-game-test y3-game-test.v2.0.bak
```

2. **下载新版本**：
```bash
git clone https://github.com/pirronewantlux529-coder/y3autohotfreshskill.git y3-game-test
```

3. **复制tools**：
```bash
cd y3-game-test
cp -r tools/* ../../tools/
```

## ✅ 升级后验证

### 测试新工具

```bash
cd <项目路径>/script/tools

# 测试lua_executor
python test_with_executor.py 1

# 应该看到：
# [成功] ✓ 命令执行完成
```

### 验证文件

确认以下文件存在：

```bash
ls tools/lua_executor.py
ls tools/test_with_executor.py
ls tools/heartbeat_monitor.py  # 已更新
```

## 🔄 迁移代码

### 旧代码

```bash
# 旧方式
python game_control.py lua "print('test')"
grep "\[error\]" "../.log/lua_player01.log"  # 手动检查
```

### 新代码（推荐）

```python
# 新方式：自动检查错误
from lua_executor import execute_lua, print_result

result = execute_lua("print('test')")
print_result(result)

if not result.success:
    exit(1)
```

## 📖 新功能使用

### 单次测试

```bash
# 命令行
python lua_executor.py "your_code"

# Python脚本
from lua_executor import execute_lua
result = execute_lua("your_code")
```

### 多步测试

```python
from lua_executor import execute_lua
import time

steps = [
    ("初始化", "lua_code_1"),
    ("执行", "lua_code_2"),
]

for desc, code in steps:
    print(f'\n[测试] {desc}')
    result = execute_lua(code)

    if not result.success:
        print(f'✗ 失败: {result.error}')
        exit(1)

    print('✓ 成功')
    time.sleep(0.5)
```

### 长时间运行

```bash
# 启动心跳监控器（实时显示）
python heartbeat_monitor.py --interval 10

# 控制台会实时显示：
# - 心跳状态
# - 发现的错误
# - 冻结和恢复事件
```

## ⚠️ 注意事项

1. **game_control.py仍然可用**
   - 旧命令不会失效
   - 但推荐使用新的 `lua_executor`

2. **heartbeat_monitor优化**
   - 输出立即刷新（实时显示）
   - 不再需要"第二天检查"

3. **SKILL.md已优化**
   - 遵循Claude官方规范
   - 删除冗余解释，只保留规则

## 🐛 常见问题

### 问题1：找不到 lua_executor 模块

**原因**：tools目录未同步

**解决**：
```bash
cd <项目>/.claude/skills/y3-game-test
cp -r tools/* ../../tools/
```

### 问题2：lua_executor 报错找不到 game_control

**原因**：Python路径问题

**解决**：在 `lua_executor.py` 同目录下运行：
```bash
cd <项目>/script/tools
python lua_executor.py "test"
```

### 问题3：想用回旧版本

**回退**：
```bash
cd <项目>/.claude/skills
rm -rf y3-game-test
mv y3-game-test.v2.0.bak y3-game-test
```

## 📚 更多文档

- [SKILL.md](./SKILL.md) - 使用规范
- [README_NEW_WORKFLOW.md](./README_NEW_WORKFLOW.md) - 完整工作流程
- [RELEASE_NOTES.md](./RELEASE_NOTES.md) - 版本更新详情

---

**升级建议**：强烈推荐升级！新版本大幅提高调试效率。
