-- 错误发送器 - 将游戏错误发送到外部监听器
-- 用法: _reloadlua('tools.error_sender')
--
-- 此模块会 hook 日志系统，将错误消息发送到 Python 监听器

local network = require 'y3.util.network'
local json = require 'y3.json'

local M = {}

-- 配置
local LISTENER_PORT = 12999

-- 客户端连接
local client = nil
local connected = false
local connecting = false

-- 消息队列（连接建立前缓存）
local messageQueue = {}
local MAX_QUEUE_SIZE = 100

-- 发送消息
local function sendMessage(data)
    if not connected then
        -- 缓存消息
        if #messageQueue < MAX_QUEUE_SIZE then
            table.insert(messageQueue, data)
        end
        return false
    end

    local jsonStr = json.encode(data)
    local packet = string.pack('>s4', jsonStr)

    local ok, err = pcall(function()
        client:send(packet)
    end)

    if not ok then
        print('[error_sender] 发送失败:', err)
        connected = false
        return false
    end

    return true
end

-- 刷新消息队列
local function flushQueue()
    if not connected then return end

    local queue = messageQueue
    messageQueue = {}

    for _, data in ipairs(queue) do
        sendMessage(data)
    end
end

-- 创建连接
local function createConnection()
    if connecting or connected then return end
    connecting = true

    print('[error_sender] 正在连接到监听器...')

    client = network.connect('127.0.0.1', LISTENER_PORT, {
        update_interval = 0.1,
        timeout = 5,
    })

    client:on_connected(function(self)
        connected = true
        connecting = false
        print('[error_sender] 已连接到监听器')

        -- 发送连接消息
        sendMessage({
            type = 'connected',
            timestamp = os.date('%H:%M:%S'),
            player = y3.player.with_local(function(p)
                return p:get_name()
            end) or 'unknown',
        })

        -- 刷新缓存的消息
        flushQueue()
    end)

    client:on_error(function(self, err)
        print('[error_sender] 连接错误:', err)
        connected = false
        connecting = false

        -- 5秒后重试
        y3.ctimer.wait(5, function()
            createConnection()
        end)
    end)

    client:on_disconnected(function(self)
        print('[error_sender] 连接断开')
        connected = false
        connecting = false

        -- 5秒后重试
        y3.ctimer.wait(5, function()
            createConnection()
        end)
    end)
end

-- Hook 日志系统
local function hookLogger()
    -- 保存原始 logger
    local originalLogger = y3.config.log.logger

    -- 设置自定义 logger
    y3.config.log.logger = function(level, message, timeStamp)
        -- 调用原始 logger
        if originalLogger then
            originalLogger(level, message, timeStamp)
        end

        -- 只发送错误级别以上的消息
        if level == 'error' or level == 'fatal' or level == 'warn' then
            sendMessage({
                type = 'error',
                level = level,
                message = message,
                timestamp = os.date('%H:%M:%S'),
            })
        end

        return false  -- 继续执行默认行为
    end

    print('[error_sender] 日志 hook 已安装')
end

-- 发送测试消息
function M.test()
    sendMessage({
        type = 'error',
        level = 'info',
        message = '[测试] 这是一条测试消息',
        timestamp = os.date('%H:%M:%S'),
    })
    print('[error_sender] 测试消息已发送')
end

-- 手动发送错误
function M.send(level, message)
    sendMessage({
        type = 'error',
        level = level or 'error',
        message = message,
        timestamp = os.date('%H:%M:%S'),
    })
end

-- 初始化
local function init()
    -- 检查是否已经初始化
    if rawget(_G, '__error_sender_inited') then
        print('[error_sender] 已初始化，跳过')
        return
    end
    rawset(_G, '__error_sender_inited', true)

    -- 创建连接
    createConnection()

    -- Hook 日志系统
    hookLogger()

    print('[error_sender] 初始化完成')
    print('[提示] 现在所有错误会发送到 Python 监听器')
end

-- 立即初始化
init()

return M
