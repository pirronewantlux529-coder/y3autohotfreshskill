# UI 测试记忆

> 测试 UI 模块（uimods/、mapwork/ui/）时阅读

## 🚨 UI 测试核心原则

**UI 代码修改后必须重启游戏！热更新对 UI 无效！**

原因：
- `ui:bindEvent` 绑定的回调在初始化时固定
- `Initui` 注册的函数只在启动时执行一次
- 模块初始化代码不会重新执行

## 🔄 UI 测试标准流程

```bash
cd "D:\Y3\ORPG项目总包\ORPG\maps\EntryMap\script\tools"

# 1. 修改 UI 代码后，必须重启
python game_control.py frestart

# 2. 等待完全进入（frestart 会自动 enter）
sleep 5

# 3. 测试 UI 功能
python game_control.py run debug_ui_xxx

# 4. 检查错误（重点看初始化阶段）
grep "\[error\]" "../.log/lua_player01.log"
```

## 📝 UI 测试脚本模板

```lua
-- tools/debug_ui_xxx.lua
local player = y3.player(1)

print('===== UI 测试 =====')

-- 获取 UI 实例
local ui = player:get_ui('ui_name')
if not ui then
    print('[error] UI 不存在')
    return
end

-- 查看 UI 节点
local node = ui:get_node('node_name')
print('节点可见:', node:is_visible())

-- 触发 UI 事件（模拟点击）
-- 注意：这只能测试逻辑，不能测试真实的用户交互
```

## 🎨 UI 节点调试

```lua
-- 遍历所有子节点
local function dump_children(node, depth)
    depth = depth or 0
    local indent = string.rep('  ', depth)
    print(indent .. node:get_name())
    for _, child in ipairs(node:get_children() or {}) do
        dump_children(child, depth + 1)
    end
end

dump_children(ui:get_root())
```

## ⚠️ UI 测试常见问题

### 问题1：UI 事件不触发
**现象**：点击按钮无反应
**可能原因**：
- 事件绑定代码有错误（检查初始化日志）
- 节点被其他透明节点遮挡
- 节点的 `interactive` 属性未设置

### 问题2：显示内容不正确
**现象**：文字/图片显示异常
**调试方法**：
```lua
-- 打印节点当前值
local text_node = ui:get_node('text1')
print('当前文本:', text_node:get_text())

local img_node = ui:get_node('img1')
print('当前图片:', img_node:get_image())
```

### 问题3：布局错乱
**检查项**：
- 锚点设置
- 父节点尺寸
- 缩放比例

## 📂 UI 模块位置

- **通用 UI 模块**：`uimods/`
- **地图专属 UI**：`mapwork/ui/`
- **基础 UI 工具**：`base/ui/`

---
*根据实际测试经验持续更新*
