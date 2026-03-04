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

### 铁律2：`[RUN-OK]` 才是成功，`[RUN-FAIL]` / exit code 非零 = 必须修复！

**game_control.py 的 `run` 和 `lua` 命令现在内置完整验证，你只看输出判定即可：**

```
发送命令 → 立即 continue（预防性释放断点）→ 1s → 再 continue → 抓错误 + 验心跳 → 输出判定
```

**脚本自动完成的事（不需要你手动做）：**
- ✅ 发命令前检查心跳，如果已卡死先自动恢复
- ✅ 收到响应后立即发 continue（预防性释放可能的断点）
- ✅ 连环断点自动多次 continue 恢复
- ✅ 同时检查 `[error]` 和 `.lua:` 两种错误模式
- ✅ 心跳验证（日志文件是否持续更新 + HEARTBEAT 标记）

| 你看到的输出 | 含义 | 操作 |
|---|---|---|
| `[RUN-OK] ... (heartbeat verified)` | 心跳正常 + 无错误 = 真正成功 | 继续下一步 |
| `[RUN-FAIL] ...` + 错误详情 | 有错误或心跳中断（已自动恢复） | **停！看错误详情，修复代码** |
| Bash exit code 非零 | 命令失败 | **停！看错误详情** |
| 无 `[RUN-` 开头输出 | Y3 Helper 或客户端异常 | 先 `python game_control.py c`，再 `launch/restart` |

**绝对禁止：**
- ❌ `[RUN-FAIL]` 后继续发命令 — 先修错误！
- ❌ 忽略错误详情里的 `.lua:行号` 信息 — 那是精确的报错位置

### 铁律3：每条 `run/lua` 必须命中命令ID成功标记！

`game_control.py` 为每条命令分配递增 `RUN-ID`，并在 Lua 侧打印：
- 成功：`[RUN-CMD-OK] id=<N>`
- 失败：`[RUN-CMD-FAIL] id=<N>`

**判定规则：**
1. 必须在超时窗口内命中本次 `id=<N>` 的成功标记。
2. 必须看到心跳（`[HEARTBEAT]`）持续。
3. 出现失败标记 / `[error]` / `xxx.lua:123:` 即失败并进入排查。

**run 脚本推荐声明：**
- `-- @run-success: [your-test] done ok=true`
- `-- @run-timeout: 20`（可选）

`game_control.py run` 会把 `@run-success` 纳入硬校验，没命中就判定失败。

**命令通道失效修复步骤：**

```bash
# 1. 重新安装 runLua 补丁
cd "D:/Y3/ORPG项目总包/ORPG/maps/EntryMap/script/.claude/skills/y3-game-test/tools"
/c/Python313/python.exe install_y3helper_runlua.py

# 2. 提醒用户重启 Cursor/VSCode

# 3. 重启游戏
cd "D:/Y3/ORPG项目总包/ORPG/maps/EntryMap/script/tools"
/c/Python313/python.exe game_control.py restart
```

**根因：Y3 Helper 插件自动更新会覆盖 extension.js，我们打的 runLua 补丁被清掉了。**

### 铁律4（原铁律3）：错误检测必须找两种模式！

**只找 `[error]` 会漏掉大量真正的 Lua 报错。必须同时检测：**

```bash
# 模式1：Lua运行时错误（最常见！格式：xxx.lua:123: error message）
grep "\.lua:" .log/lua_player01.log | tail -20

# 模式2：框架级错误标记
grep "\[error\]" .log/lua_player01.log | tail -20
```

**两个都返回空才算通过。任何一个有输出 = 测试失败，必须修复。**

### 铁律5（原铁律4）：游戏启动后必须挂 Watchdog！

**游戏启动/重启后，必须立即后台启动 Watchdog 持续监控。这不是可选项。**

```bash
# 等到第一个心跳出现后，立即启动（用 run_in_background=true）
python tools/game_watchdog.py --max-failures 3
```

Watchdog 会 24 小时挂着，自动捕获断点/卡死/报错。收到报警 → **先诊断修复，避免盲目重复重启**。

**Watchdog 参数：**
- `--max-failures 3`：连续恢复失败3次后 exit(1) 通知 Claude
- `--stale-timeout 45`：心跳超时判定（Y3日志有~27s缓冲延迟，45s=延迟+容错）
- `--check-interval 15`：健康检查间隔

**Watchdog 自动恢复策略：**

| 问题 | 操作 | 失败则 |
|------|------|--------|
| crashed（进程死亡） | 直接 launch/restart | — |
| error（Lua报错） | continue 释放断点 | restart |
| stale（心跳超时） | continue + 验证恢复 | restart |

---

## `run` / `lua` 命令输出解读

| 输出 | 含义 | 操作 |
|------|------|------|
| `[RUN-OK] ... (cmd_id=N, heartbeat verified)` | 命中命令ID成功标记 + 心跳正常 | 继续 |
| `[RUN-FAIL] ...` + 错误详情 | 有错误（已自动恢复断点） | **停！看错误详情，修复代码** |
| Bash exit code 非零 | 命令失败 | **停！看错误详情** |
| 无 `[RUN-` 输出 | Y3 Helper 断连或客户端异常 | `python game_control.py launch` 或 `restart` |

**注意：`run` 和 `lua` 命令都有完整的心跳验证，不需要手动 continue 或查日志。**

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
| `reload [module]` | 热更新 Lua |
| `restart` | 重启游戏（调用 tools.restart_game） |
| `c` | 恢复断点 |
| `lua "代码"` | 执行行内Lua |
| `run 脚本名` | 执行 tools/ 下脚本 |
| `test` | 发送一条测试 lua |

## 热更新 vs 重启

- **热更新有效**：`tools/` 脚本、数据表
- **必须重启**：UI回调、模块init、Initui、greathero
- **经验法则**：改了 UI 回调或初始化逻辑，优先 `restart` 后再测

## 截图验证

改了 UI 布局/显示/特效时，建议配合外部截图工具或引擎自带截图功能进行人工确认。

## 异常处理

```bash
# 查看 Y3 Helper 异常消息
tail -20 "$TEMP/y3helper_messages.jsonl"

# 恢复断点
python game_control.py c

# 恢复失败 → 重启
python game_control.py restart
```

## 标准测试流程

```bash
cd tools/

# 1. 启动
python game_control.py launch
sleep 20

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

---

## 🧠 记忆系统

Claude 具备跨会话记忆能力，通过 `memory/` 目录积累和复用调试经验。

### 工作开始时

1. **必读**：`Read memory/main.md`
2. **按需读取**：根据任务类型读取 `skill-test.md` / `ui-test.md` / `equip-test.md`

### 遇到错误时

先搜索已有经验再从头调试：

```bash
# 在 learned 记忆中搜索关键词
grep -r "关键词" memory/learned/
```

找到匹配 → 读取该文件，按已有方案处理。未找到 → 正常调试。

### 解决问题后（自动记忆）

解决**非平凡问题**后（花费 >5min / 发现 API 怪癖 / 找到更好方法），在 `memory/learned/` 创建或更新记忆：

- 文件名：`{类别}_{主题}.md`（类别：`error` / `api` / `workflow` / `debug` / `config`）
- 必填字段：标题、Category、Created、场景、问题、解决方案
- 详细格式见 `memory/README.md`

**不记录**：简单拼写错误、已有记忆覆盖的内容。

---

## 🐍 Python 工具扩展

当重复操作出现时，主动创建 Python 辅助脚本，避免手动重复。

### 触发条件（满足任一即创建）

- 同一操作手动执行 **2 次以上**
- 需要封装复杂的多步管道（日志分析 + 数据提取 + 格式化）
- 批量测试场景（多组参数 / 多个模块）

### 存放位置

```
script/tools/extensions/ext_{用途}.py
```

例如：`ext_log_analyzer.py`、`ext_batch_tester.py`、`ext_data_extractor.py`

### 创建规范

- 使用 `C:\Python313\python.exe` 执行
- 脚本开头设置正确路径（参考 `EXTENSIONS_GUIDE.md` 模板）
- 与 `game_control.py` 通过 CLI 接口交互（`subprocess.run`），不直接 import 内部函数
- 创建后在 `memory/learned/` 记录用途：`workflow_ext_{脚本名}.md`

### 不创建的条件

- ❌ 一次性调试操作
- ❌ 简单 grep / 单条 game_control 命令
- ❌ `game_control.py` 已有的功能（run / lua / restart 等）
