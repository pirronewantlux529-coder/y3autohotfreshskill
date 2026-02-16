---
name: y3-game-test
description: 通过Y3 Helper执行Lua代码并自动检测错误，启动游戏、热更新模块、运行测试脚本。用于测试游戏功能、调试Lua代码、验证代码修改的任务。
---
# Y3测试流程

## 🔴🔴🔴 三条铁律（违反任何一条 = 测试完全作废）

### 铁律1：发代码前必须审查！

**你写的 lua/run 代码本身就可能有错！发之前必须逐行检查：**

- 变量名是否拼写正确？API 是否存在？（不确定就 Grep 搜）
- `y3.player(1)` 不是 `player`，tools 脚本里没有 `player` 全局变量
- 字符串拼接用 `..` 不是 `+`，nil 拼接会崩
- 方法调用用 `:` 不是 `.`（`unit:get_name()` 不是 `unit.get_name()`）
- **行内 lua 命令只适合单行简单语句，超过一行必须写 tools/ 脚本文件**

**你发出去的调试代码如果有错，会触发断点冻结游戏，然后你连原始 bug 都看不到了。**

### 铁律2：拿不到数据 / 没有输出 = 游戏断点了！必须恢复！

**Y3引擎代码出错 → 触发断点 → 游戏冻结（包括日志写入）。不恢复就永远看不到错误。**

**⚠️ 以下任何一种情况出现，都必须立即执行恢复流程，绝不能跳过或放弃：**

| 你看到的现象 | 原因 | 必须做 |
|---|---|---|
| lua/run 命令没有任何 print 输出 | 代码有错，触发断点 | 恢复 → 查日志 |
| lua/run 命令返回了但数据是空的/不对 | 代码在中途崩了 | 恢复 → 查日志 |
| 连续多条命令都拿不到预期结果 | 第一条就断点了，后面全无效 | 恢复 → 查日志 |
| `[RUN-FAIL]` 或 Bash exit code 非零 | 执行失败 | 恢复 → 查日志 |

**恢复流程（每次都是这三步，不能省）：**

```bash
# 1. 恢复断点
python game_control.py c

# 2. 查 Lua 错误（两种模式！）
grep "\.lua:" .log/lua_player01.log | tail -20
grep "\[error\]" .log/lua_player01.log | tail -20

# 3. 根据错误修复代码，再重试
```

**绝对禁止：**
- ❌ 拿不到数据就放弃，不查原因 — **这是最常犯的错误！**
- ❌ 心跳停了还继续发命令 — 游戏已冻结，后续命令全部无效
- ❌ 不恢复断点就直接换思路/换方法 — 游戏还卡着，换什么都没用

**心跳判断**：日志中 >15秒没有新的 `[HEARTBEAT]` = 断点了。但游戏刚启动时没心跳是正常的，等第一个 `[HEARTBEAT]` 出现后此规则才生效。

**`run` 命令已内置自动恢复**（心跳停止 → 自动 continue → 返回 `[RUN-FAIL]`），但 `lua` 命令没有，必须手动 `python game_control.py c`。

### 铁律3：错误检测必须找两种模式！

**只找 `[error]` 会漏掉大量真正的 Lua 报错。必须同时检测：**

```bash
# 模式1：Lua运行时错误（最常见！格式：xxx.lua:123: error message）
grep "\.lua:" .log/lua_player01.log | tail -20

# 模式2：框架级错误标记
grep "\[error\]" .log/lua_player01.log | tail -20
```

**两个都返回空才算通过。任何一个有输出 = 测试失败，必须修复。**

### 铁律4：游戏启动后必须挂 Watchdog！

**游戏启动/frestart 成功进入后，必须立即后台启动 Watchdog 持续监控。这不是可选项。**

```bash
# 等到第一个心跳出现后，立即启动（用 run_in_background=true）
python tools/game_watchdog.py --max-failures 3
```

Watchdog 会 24 小时挂着，自动捕获断点/卡死/报错。收到报警 → **先诊断修复，禁止盲目 frestart**。

**Watchdog 参数：**
- `--max-failures 3`：连续恢复失败3次后 exit(1) 通知 Claude
- `--stale-timeout 45`：心跳超时判定（Y3日志有~27s缓冲延迟，45s=延迟+容错）
- `--check-interval 15`：健康检查间隔

**Watchdog 自动恢复策略：**

| 问题 | 操作 | 失败则 |
|------|------|--------|
| crashed（进程死亡） | 直接 frestart | — |
| error（Lua报错） | continue 释放断点 | frestart |
| stale（心跳超时） | continue + 验证恢复 | frestart |

---

## `run` 命令输出解读

| 输出 | 含义 | 操作 |
|------|------|------|
| `[RUN-OK]` | 成功 | 继续 |
| `[RUN-FAIL]` | 失败 | **停！分析错误，修复代码** |
| 没有 `[RUN-` 开头 | 游戏卡死 | `python game_control.py frestart` |
| Bash exit code 非零 | 命令失败 | **停！分析错误** |
| 没有任何 print 输出 | 100%有错误 | 恢复断点 → 查日志 |

## `run` vs `lua` 命令

```bash
# run = 执行 tools/ 下的脚本文件（推荐）
python game_control.py run my_test      # 执行 tools/my_test.lua

# lua = 执行行内代码（只适合单行）
python game_control.py lua "print('hello')"

# ❌ run 不支持行内代码！
python game_control.py run "print('hello')"  # 错误！
```

### 行内 Lua 常见语法陷阱

```lua
-- ❌ h:method() 括号被 shell 或 Y3 wrap_code 误解析
print('[状态] battle='..tostring(h:is_in_battle()))

-- ❌ ~= 在字符串拼接中可能导致解析异常
tostring(h.timer~=nil)

-- ❌ player 不是全局变量
local h = player.mainhero
```

**超过一行 → 必须写 tools/ 脚本文件，别用行内。**

## Hook 自动防护

PostToolUse Hook 会自动检查每次 Bash 执行后的日志。如果 hook block 了你：
- 不要忽略！block 消息里有错误详情
- 必须修复后重试

## game_control.py 命令速查

| 命令 | 功能 |
|------|------|
| `launch` | 启动游戏 |
| `enter` | 进入游戏 |
| `kill` | 杀进程 |
| `frestart` | 强制重启（kill → launch → enter） |
| `status` | 检查状态 |
| `c` | 恢复断点 |
| `lua "代码"` | 执行行内Lua |
| `run 脚本名` | 执行 tools/ 下脚本 |
| `ss` | 截图 |

## 热更新 vs 重启

- **热更新有效**：`tools/` 脚本、数据表
- **必须重启**：UI回调、模块init、Initui、greathero
- **经验法则**：改了 `uimods/`、`mapwork/ui/` → 直接 `frestart`

## 截图验证

改了 UI 布局/显示/特效 → 日志不够，必须截图确认：
```bash
python game_control.py ss
# 然后用 Read 查看 C:/screenshot_temp/game_screenshot.png
```

## 异常处理

```bash
# 查看 Y3 Helper 异常消息
tail -20 "$TEMP/y3helper_messages.jsonl"

# 恢复断点
python game_control.py c

# 恢复失败 → 强制重启
python game_control.py frestart
```

## 标准测试流程

```bash
cd tools/

# 1. 启动并进入
python game_control.py frestart
sleep 25

# 2. 确认第一个心跳出现后，启动 Watchdog（run_in_background=true）
python tools/game_watchdog.py --max-failures 3

# 3. 执行测试（写好脚本文件再 run）
python game_control.py run my_test

# 4. 检查错误（两种模式都查！）
grep "\.lua:" ../.log/lua_player01.log | tail -20
grep "\[error\]" ../.log/lua_player01.log | tail -20
```

## tools/ 脚本模板

```lua
-- tools/my_test.lua
local p = y3.player(1)        -- ✅ 用 y3.player 获取
local h = p.mainhero           -- ✅
-- local h = player.mainhero   -- ❌ player 不是全局变量

print('[测试] 开始')
-- 你的测试逻辑
print('[测试] 完成')
```
