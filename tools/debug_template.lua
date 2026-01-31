-- 调试脚本模板
-- 用法: python game_control.py run debug_template
-- 复制此文件并修改为你需要的调试逻辑

local player = y3.player(1)

-- 检查是否在游戏中
if not player.mainhero then
    print("[调试] 错误: 请先进入游戏")
    return
end

print("========== 调试开始 ==========")

-- 获取存档数据
local save = player:get_current_save()

-- 打印一些基本信息
print("玩家ID:", player:get_id())
print("存档数据类型:", type(save))

-- TODO: 在这里添加你的调试代码
-- 例如:
-- print("金币:", save.gold)
-- print("等级:", save.level)

print("========== 调试结束 ==========")
