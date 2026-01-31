-- 重启游戏（切换关卡）
-- 用法: python game_control.py restart
-- 注意: level_id 需要根据你的项目修改

print("[重启] 正在切换关卡...")

-- TODO: 修改为你的 level_id
-- 可以在 Y3 编辑器中找到关卡ID
local level_id = '615ac83d-ae12-11ef-b9b9-9d56ad7167b1'

y3.game.switch_level(level_id)
