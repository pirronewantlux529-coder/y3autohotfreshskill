# 技能测试记忆

> 测试 Lua 技能（宠物/怪物/主角技能）时阅读

## 🎯 技能测试前置条件

1. **游戏已进入** - 执行过 `enter` 命令
2. **角色已获得** - `player.mainhero` 不为 nil
3. **如果测试宠物技能** - 确保宠物已出战

## 📝 技能测试脚本模板

```lua
-- tools/debug_skill_xxx.lua
local player = y3.player(1)
local hero = player.mainhero  -- 注意：是属性不是方法！

if not hero then
    print('[error] 角色不存在，请先 enter')
    return
end

local save = player:get_current_save()

print('===== 技能测试 =====')

-- 获取技能（需要先搜索验证实际 API）
-- rg "get_skill" --type lua 查找正确的方法名
```

## 🐾 宠物技能测试

```lua
-- 获取出战宠物
local save = player:get_current_save()
local petId = save.petdata.CurrentPet

if not petId or petId == '' then
    print('[error] 没有出战宠物')
    return
end

-- 获取宠物单位
local petUnit = -- 需要根据项目实际获取方式
```

## ⚠️ 技能测试常见问题

### Buff 不生效
- 检查 buff 是否正确注册到 `buff_list`
- 检查 buff 事件是否正确绑定

### 技能伤害不正确
- 检查伤害公式中的属性读取
- 检查伤害类型（物理/魔法/真实）

### 技能无法释放
- 检查冷却时间
- 检查释放条件
- 检查目标选择

---
*根据实际测试经验持续更新*
