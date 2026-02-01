// 测试 Y3 Helper 补丁是否能正常工作
// 在 Node.js 环境中运行此脚本来验证

const net = require("net");

const LISTENER_PORT = 12999;

console.log("测试连接到监听器...");

const sock = new net.Socket();
sock.setTimeout(1000);

sock.connect(LISTENER_PORT, "127.0.0.1", () => {
    console.log("已连接到监听器");

    const data = JSON.stringify({
        type: "print",
        level: "info",
        message: "[测试] 来自 Node.js 的测试消息",
        timestamp: new Date().toLocaleTimeString()
    });

    const len = Buffer.alloc(4);
    len.writeUInt32BE(Buffer.byteLength(data));

    sock.write(Buffer.concat([len, Buffer.from(data)]));
    console.log("已发送测试消息:", data);

    sock.end();
    console.log("连接已关闭");
});

sock.on("error", (err) => {
    console.error("连接错误:", err.message);
});

sock.on("close", () => {
    console.log("Socket 已关闭");
});
