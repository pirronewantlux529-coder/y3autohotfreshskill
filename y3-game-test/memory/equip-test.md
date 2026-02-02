# 装备系统测试记忆

> 测试装备相关功能（穿戴/属性/强化/升华）时阅读

## 🎯 装备测试前置条件

1. **游戏已进入** - 执行过 `enter` 命令
2. **角色已获得** - `player.mainhero` 不为 nil

## 📝 装备测试脚本模板

```lua
-- tools/debug_equip_xxx.lua
local player = y3.player(1)
local hero = player.mainhero  -- 注意：是属性不是方法！
local save = player:get_current_save()

if not hero then
    print('[error] 角色不存在')
    return
end

print('===== 装备测试 =====')

-- 查看当前装备
local equips = save.equips or {}
for slot, equipData in pairs(equips) do
    print(string.format('槽位 %s: %s', slot, equipData.id or 'nil'))
end

-- 查看角色属性（需要先搜索验证实际 API）
-- rg "get_attr\|:attr" --type lua 查找正确的方法名
```

## 🔧 装备系统三层架构

测试装备时需要验证三层都正确：

### 1. 显示层
- UI 正确显示装备图标
- 属性面板数值正确
- 强化等级正确显示

### 2. 计算层
- 基础属性正确计算
- 强化加成正确
- 套装效果正确

### 3. 检测层
- 装备条件检测（等级/职业）
- 穿戴互斥检测
- 背包空间检测

## ⚠️ 装备测试常见问题

### 问题1：属性不生效
**检查顺序**：
1. 装备数据是否正确保存到 save
2. 属性计算函数是否被调用
3. 属性是否正确应用到单位

### 问题2：穿脱装备后属性异常
**关键点**：属性变化时序
```lua
-- 正确顺序：
-- 1. 移除旧装备属性
-- 2. 更新装备状态
-- 3. 添加新装备属性
```

### 问题3：死循环
**原因**：属性变化触发事件，事件又触发属性变化
**解决**：用函数参数控制，不用全局变量
```lua
function update_equip(player, skip_refresh)
    -- 更新装备逻辑
    if not skip_refresh then
        refresh_attrs(player, true)  -- 传递标记防止循环
    end
end
```

## 📂 装备系统相关文件

- **装备核心**：`base/items/equip.lua`
- **强化系统**：`uimods/reinforcement.lua`
- **升华系统**：参见 `analysis/upgrade_system_rules.md`

---
*根据实际测试经验持续更新*
