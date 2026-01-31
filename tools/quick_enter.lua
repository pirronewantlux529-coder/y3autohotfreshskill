-- 快速进入游戏脚本
-- 用法: python game_control.py enter

local player = y3.player(1)

-- 检查是否已进入游戏
if player.mainhero then
    print("[快速进入] 已在游戏中，无需重复进入")
    return
end

print("[快速进入] 模拟点击开始游戏...")

-- 获取start_menu模块
local start_menu = require 'uimods.start_menu'
local path = start_menu.path
local uimod = y3.ui

-- 隐藏菜单界面
if path and path['主界面'] then
    local ui = uimod.get_ui(player, path['主界面'])
    if ui then
        ui:set_visible(false)
    end
end

if path and path['选人界面'] then
    local ui = uimod.get_ui(player, path['选人界面'])
    if ui then
        ui:set_visible(false)
    end
end

-- 设置存档并加载英雄
player.savetab = player.savetab or {}
player.savetab.selectsave = player.savetab.selectsave or 1
local currentsave = player:get_current_save()
local unlocknd = currentsave.lastnd or 1
require 'uimods.ndselect'.set_map_nd(unlocknd)
print(string.format("[快速进入] 加载存档 %d ...", player.savetab.selectsave))
require('base.unit.save').loadhero(player, player.savetab.selectsave)
