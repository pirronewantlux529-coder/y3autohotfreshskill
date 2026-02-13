# y3-game-test Skill 更新日志

## [3.0.0] - 2026-02-13

### 新增功能 🎉

#### Game Watchdog（后台持久监控）
- **新增 `game_watchdog.py`**：Claude Code 后台 Task，持续监控游戏健康状态
- **时间戳心跳检测**：解析日志中 `[HEARTBEAT]` 行的时间戳，精确判断游戏是否存活（替代旧的文本存在性检查）
- **STARTUP 等待阶段**：启动后自动等待游戏心跳正常（最长120秒），避免加载期间误报
- **三级恢复策略**：`crashed` → frestart / `error` → continue → frestart / `stale` → continue+verify → frestart
- **结构化退出报告**：自动恢复连续失败 N 次后 exit(1)，输出 Claude 可直接解析的错误报告

#### 心跳机制（`[HEARTBEAT]`）
- **新增心跳定时器**：`base/debugs.lua` 每 5 秒打印 `[HEARTBEAT]`，供 watchdog 和 run 命令检测
- **`game_control.py` 更新**：心跳检测同时支持 `AutoPlayer` 和 `[HEARTBEAT]` 标记
- **Y3 日志缓冲发现**：Y3 引擎有 ~27 秒文件 I/O 缓冲延迟，stale_timeout 设为 45 秒以避免误判

#### SKILL.md 重大更新
- **新增「最高铁律」章节**：没有打印 = 100%有错误，明确 run 命令输出解读表
- **新增 `run` 命令常见错误及规避**：行内 Lua 语法陷阱、正确的脚本文件写法
- **新增 Watchdog 完整章节**：启动流程、参数表、恢复策略、Claude 通知处理
- **核心铁律简化**：run 命令已内置自动恢复，frestart 已内置 enter 步骤

#### Y3_HELPER_SETUP.md 更新
- **新增步骤 7b**：心跳定时器配置（game_watchdog 必需）
- **新增步骤 9**：Watchdog 验证步骤，含预期输出
- **新增故障排除**：Watchdog 心跳误报（stale false positive）解决方案
- **更新确认清单**：新增 `[HEARTBEAT]` 和 watchdog 验证项

### 技术细节

- Watchdog 默认参数：`check-interval=15s` / `stale-timeout=45s` / `max-failures=3` / `timeout=86400s`
- 心跳时间戳格式：`[MM-DD HH:MM:SS.mmm]`，从日志末尾反向搜索最近的 `[HEARTBEAT]` 行
- 恢复历史记录：保留最近 20 条记录，用于智能跳过重复失败的恢复动作
- Windows 兼容：所有输出使用 ASCII/英文，PowerShell 窗口隐藏

### 向后兼容性

✅ 完全向后兼容。Watchdog 为可选功能，不安装心跳定时器不影响现有命令。心跳检测同时兼容 `AutoPlayer`（旧）和 `[HEARTBEAT]`（新）。

---

## [2.1.0] - 2026-02-13

### 新增功能 🎉

#### 游戏窗口截图 (`screenshot` / `ss`)
- **新增 `game_control.py screenshot` 命令**：截取Y3游戏窗口画面，不抢焦点
- **技术方案**：DXcam（Desktop Duplication API）+ 短暂置前台 + 自动切回，支持 DirectX 渲染内容
- **窗口精确定位**：通过窗口类名排除 Console/Helper 窗口，精准捕获游戏渲染窗口
- **Python API**：`from game_control import screenshot; path = screenshot()`

#### 截图验证指南
- **SKILL.md 新增截图验证章节**：明确何时需要截图验证（UI 修改必须截图，纯逻辑修改可选）
- **标准流程**：重启游戏 → 日志检查 → 截图验证 → 确认画面效果

### 技术细节

- 使用 `win32gui.EnumWindows` + 窗口类名过滤精确定位游戏窗口（避免标题歧义）
- `SetForegroundWindow` 短暂置前台约0.5秒，截完自动 `SetForegroundWindow` 切回原窗口
- 截图保存在固定英文路径 `C:/screenshot_temp/` 避免 Unicode 编码问题
- 新增依赖：`pywin32`、`dxcam`、`Pillow`
- 新增 `_get_hidden_startupinfo()` 工具函数防止 PowerShell 弹窗抢焦点

### 向后兼容性

✅ 完全向后兼容。截图功能为纯新增，不影响现有命令。依赖库为可选安装，未安装时会给出友好提示。

---

## [2.0.0] - 2025-02-12

### 新增功能 🎉

#### 命令中断检测与恢复流程
- **心跳包检测机制**：通过检查AutoPlayer状态报告判断游戏是否中断
- **4步恢复流程**：
  1. 发送命令后等待5-8秒
  2. 检查心跳包
  3. 如果心跳停止 → continue → 检查错误 → 修复 → 重试
  4. 如果心跳正常但无输出 → 检查文件路径、模块名等

#### 错误检测铁律
- **新增正确的错误检测方法**：使用 `grep "\.lua:"` 替代 `grep "\[error\]"`
- **原理**：Lua报错一定包含 `.lua:行号` 格式，比 `[error]` 标签更可靠
- **新增禁止项**：❌ 只查 `[error]` 而不查 `.lua:`

### 优化改进 ✨

#### 文档结构优化（符合Claude官方Skill规范）
- 标题精简：`Y3游戏测试` → `Y3测试流程`
- 删除冗余emoji：只保留🚨标记核心铁律
- 章节标题简化：
  - `🚀 标准测试流程` → `标准测试流程`
  - `🤖 Orders - 自动化命令库` → `Orders自动化命令库`
  - `📚 API` → `API参考`
  - `📝 测试代码模板` → `测试代码模板`
  - `💓 心跳监控器` → `心跳监控器`
  - `🔥 热更新生效条件` → `热更新生效条件`
  - `🚨 异常处理` → `异常处理`

#### 表述优化
- 删除"强制要求！"等主观语气
- 删除"核心理念：能用命令模拟的，就不让用户手动操作！"营销性表述
- 删除"原因："等解释性段落，保持客观专业

### 技术细节

#### Description保持不变（已符合规范）
```yaml
description: 通过Y3 Helper执行Lua代码并自动检测错误，启动游戏、热更新模块、运行测试脚本。用于测试游戏功能、调试Lua代码、验证代码修改的任务。
```
- ✅ 第三人称
- ✅ 包含技术关键词
- ✅ 明确触发条件

### 升级建议

使用此skill的开发者应注意：

1. **必须学习心跳检测流程**：这是最重要的新增功能，可以节省大量调试时间
2. **更新错误检测命令**：将所有 `grep "\[error\]"` 替换为 `grep "\.lua:"`
3. **熟悉4步恢复流程**：命令中断时的标准处理方式

### 向后兼容性

✅ 完全向后兼容，所有原有功能保持不变，仅新增功能和优化文档。

---

**版本对比**：
- v1.0.0：基础测试流程
- v2.0.0：新增心跳检测、错误检测优化、文档规范化
- v2.1.0：游戏窗口截图、截图验证指南
- v3.0.0：Game Watchdog 后台监控、`[HEARTBEAT]` 心跳机制、STARTUP 等待阶段
