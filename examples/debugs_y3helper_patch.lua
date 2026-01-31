--[[
    Y3 Helper 调试环境 - debugs.lua 补丁

    复制此文件内容到 base/debugs.lua

    前置条件：main.lua 中需要有以下代码加载 debugs.lua：
    if debug.sethook then     --是本地开发环境
        y3.config.debug = true
        require 'base.debugs' --debug功能开启
    end
]]

---重载lua文件
---@param name string lua文件名
---@return table|nil|any 重载代码
function _reloadlua(name)
    package.loaded[name]=nil
    return require (name)
end

print('---------------当前为本地环境，可进行调试----------------------')

y3.game:event('键盘-按下', y3.const.KeyboardKey['F5'], function ()
    print('-----------------热调试内容------------------------')
    _reloadlua('base.hotfresh')
    print('-----------------热调试内容结束------------------------')
end)

-- 确保 Y3 Helper 的 command 处理器正确注册
-- 解决 .rd 热更新广播有时无法接收的问题
if y3.develop and y3.develop.helper then
    local helper = y3.develop.helper
    helper.onReady(function()
        helper.registerMethod('command', function(params)
            if params and params.data then
                y3.develop.console.input(params.data)
            end
        end)
        print('[debugs] Y3 Helper command 处理器已注册')
    end)
end
