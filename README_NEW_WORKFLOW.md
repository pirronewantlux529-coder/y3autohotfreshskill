# Y3 Game Test 优化工作流程

## 🎯 核心问题解决

### 之前的问题

1. **发送Lua代码后不知道是否真正成功**
   - `game_control.py lua` 只确认游戏收到命令
   - 但代码执行中的错误（nil访问、逻辑错误）不会反馈
   - 以为成功了，实际上游戏已经卡死或报错

2. **监听系统和命令流割裂**
   - `heartbeat_monitor.py` 独立运行
   - `file_listener.py` 独立显示日志
   - 命令发送后需要手动查日志确认

3. **错误发现滞后**
   - 发现问题时已经执行了很多步
   - 不知道是哪一步出错的
   - 调试效率低

### 现在的解决方案

**核心理念：每次命令执行后立即验证，就像术后必查CT**

```
发送Lua代码
    ↓
等待响应（确认游戏收到）
    ↓
检查新增的日志错误 ← 自动完成
    ↓
检查新增的异常消息 ← 自动完成
    ↓
返回明确的成功/失败结果
```

## 🔧 新工具：lua_executor.py

### 设计目标

- **自动错误检测**：无需手动检查日志
- **结构化结果**：清晰的成功/失败/错误信息
- **自动恢复**：游戏卡死时自动尝试 continue
- **易于集成**：Python API + 命令行都可用

### 核心功能

```python
from lua_executor import execute_lua, print_result

result = execute_lua("your_lua_code")

# result 包含完整信息：
# - success: 是否成功（无错误）
# - executed: 游戏是否响应
# - alive: 游戏是否存活
# - log_errors: 新增的日志错误列表
# - exceptions: 新增的异常列表
# - error: 主要错误描述
# - warning: 警告信息
```

### 实现原理

1. **记录执行前状态**
   ```python
   log_line_before = get_log_line_count()
   msg_line_before = get_msg_line_count()
   ```

2. **发送命令并等待**
   ```python
   response = run_lua_with_confirm(code, timeout=10)
   ```

3. **检查新增错误**
   ```python
   time.sleep(0.3)  # 给日志刷新时间
   log_errors = get_new_log_errors(log_line_before)
   exceptions = get_new_exceptions(msg_line_before)
   ```

4. **返回结构化结果**
   ```python
   result.success = (not log_errors and not exceptions)
   ```

## 📊 工作流程对比

### 旧流程（容易出错）

```bash
# 1. 发送命令
python game_control.py lua "some_code"
# 输出: [成功] 游戏已执行命令

# 2. 不知道是否真的成功，需要手动查日志
grep "\[error\]" ../.log/lua_player01.log  # ← 经常忘记做！

# 3. 如果有错误，还要查异常
grep "exception" "$TEMP/y3helper_messages.jsonl"

# 4. 游戏卡死了也不知道
```

**问题**：
- ❌ 步骤多，容易遗漏
- ❌ 需要手动判断
- ❌ 不知道哪一步出错

### 新流程（自动可靠）

```python
from lua_executor import execute_lua, print_result

result = execute_lua("some_code")
print_result(result)
# 输出:
# [成功] ✓ 命令执行完成
# 或
# [失败] ✗ 执行中发现: 2个异常, 1个日志错误
# [异常] 发现 2 个引擎异常:
#   • attempt to call a nil value
#   • ...
```

**优势**：
- ✅ 一步完成，无需手动查日志
- ✅ 自动判断成功/失败
- ✅ 清晰显示所有错误
- ✅ 可在Python中直接判断

## 🎯 使用场景

### 场景1：开发调试（单次测试）

**推荐：lua_executor**

```python
#!/usr/bin/env python
from lua_executor import execute_lua, print_result

# 测试你的功能
code = """
    local player = y3.player(1)
    local save = player:get_current_save()
    print('[测试] 装备数量:', #save.equips)
"""

result = execute_lua(code)
print_result(result, verbose=True)

if not result.success:
    print('\n[调试] 发现问题，需要修复')
    exit(1)
```

**为什么不用心跳监控器**：
- 单次测试不需要持续监控
- lua_executor 已经自动检查错误
- 执行快速，不会长时间卡死

### 场景2：长时间运行（压力测试/过夜）

**推荐：heartbeat_monitor**

```bash
# 1. 启动游戏
python game_control.py launch && sleep 20
python lua_executor.py --file quick_enter && sleep 8

# 2. 启动心跳监控器（后台）
python heartbeat_monitor.py --interval 10 &

# 3. 启动长时间任务
python lua_executor.py --file fakeplayer_start
```

**为什么需要心跳监控器**：
- 长时间运行可能在任何时刻卡死
- 心跳监控器可以自动恢复
- 记录所有冻结和恢复事件
- 第二天查看监控日志即可

### 场景3：自动化测试脚本

**结合使用：lua_executor + 多步验证**

```python
#!/usr/bin/env python
from lua_executor import execute_lua, print_result
import sys

def test_equipment_system():
    """测试装备系统"""

    # 步骤1：给装备
    result = execute_lua("_reloadlua('tools.give_pet_equips')")
    if not result.success:
        print('[步骤1失败] 给装备失败')
        return False

    # 步骤2：检查装备数量
    result = execute_lua("""
        local p = y3.player(1)
        local s = p:get_current_save()
        assert(#s.equips > 0, '装备数量为0')
        print('[测试] 装备数量:', #s.equips)
    """)
    if not result.success:
        print('[步骤2失败] 装备数量检查失败')
        return False

    # 步骤3：穿戴装备
    result = execute_lua("""
        local equip = require('base.items.equip')
        equip.wear_equipment(1, 1)  -- 穿戴第1个装备到第1个槽位
    """)
    if not result.success:
        print('[步骤3失败] 穿戴装备失败')
        return False

    print('[OK] 装备系统测试通过！')
    return True

if __name__ == '__main__':
    success = test_equipment_system()
    sys.exit(0 if success else 1)
```

## 🔄 与现有工具的关系

### lua_executor vs game_control.py

- **lua_executor** = game_control + 自动错误检查
- game_control 仍然保留，用于特殊情况
- 推荐优先使用 lua_executor

### lua_executor vs heartbeat_monitor

| 特性 | lua_executor | heartbeat_monitor |
|------|:------------:|:-----------------:|
| 单次命令错误检测 | ✅ | ❌ |
| 自动恢复卡死 | ✅ | ✅ |
| 持续监控 | ❌ | ✅ |
| 长时间无人值守 | ❌ | ✅ |
| Python API集成 | ✅ | ❌ |

**结论**：
- 开发调试 → lua_executor
- 长时间运行 → heartbeat_monitor
- 自动化测试 → lua_executor

### lua_executor vs file_listener

- **file_listener**: 实时显示日志（人工查看）
- **lua_executor**: 自动检查错误（程序判断）
- 可以同时使用（file_listener 用于查看详细输出）

## 📝 最佳实践

### 1. 开发时的标准流程

```python
# test_my_feature.py
from lua_executor import execute_lua, print_result

# 测试代码
result = execute_lua("""
    -- 你的测试代码
""")

# 显示结果
print_result(result, verbose=True)

# 程序化判断
if not result.success:
    exit(1)
```

### 2. 多步骤测试的模式

```python
steps = [
    ("步骤1描述", "lua_code_1"),
    ("步骤2描述", "lua_code_2"),
    ("步骤3描述", "lua_code_3"),
]

for i, (desc, code) in enumerate(steps, 1):
    print(f'\n[步骤{i}] {desc}')
    result = execute_lua(code)

    if not result.success:
        print(f'✗ 步骤{i}失败')
        print_result(result, verbose=True)
        exit(1)

    print(f'✓ 步骤{i}成功')
    time.sleep(0.5)

print('\n[OK] 所有步骤完成！')
```

### 3. 错误恢复的处理

```python
result = execute_lua("risky_code()")

if not result.success:
    if not result.alive:
        # 游戏卡死
        print('[严重] 游戏卡死，需要重启')
        # 可以调用 game_control.py frestart
    elif result.exceptions:
        # 引擎异常
        print('[异常] 代码触发引擎异常:')
        for exc in result.exceptions:
            print(f'  • {exc}')
    elif result.log_errors:
        # Lua逻辑错误
        print('[错误] Lua逻辑错误:')
        for err in result.log_errors:
            print(f'  • {err}')
```

## 🚀 迁移指南

### 从旧方式迁移

**旧代码**：
```python
import game_control

game_control.run_lua_code("print('test')")
# 需要手动查日志...
```

**新代码**：
```python
from lua_executor import execute_lua, print_result

result = execute_lua("print('test')")
print_result(result)  # 自动显示结果和错误
```

### 从game_control.py命令行迁移

**旧方式**：
```bash
python game_control.py lua "print('test')"
grep "\[error\]" ../.log/lua_player01.log
```

**新方式**：
```bash
python lua_executor.py "print('test')"
# 自动显示错误，无需额外命令
```

## 📖 相关文件

| 文件 | 说明 |
|------|------|
| `tools/lua_executor.py` | 新的执行器（自动错误检测） |
| `tools/game_control.py` | 旧的控制脚本（仍可用） |
| `tools/heartbeat_monitor.py` | 心跳监控器（长时间运行） |
| `tools/file_listener.py` | 日志监听器（实时查看） |
| `tools/test_with_executor.py` | 使用示例 |

## 🎓 总结

**优化的核心思想**：
1. **每次执行都验证**：不等到最后才发现问题
2. **自动化检测**：减少人工判断
3. **结构化反馈**：程序可以直接判断成功失败
4. **分场景工具**：短期用lua_executor，长期用heartbeat_monitor

**记住**：
- ✅ 开发测试 → lua_executor
- ✅ 长时间运行 → heartbeat_monitor
- ✅ 所有Lua执行都应该检查错误
- ✅ 发送命令后立即验证，不拖延
