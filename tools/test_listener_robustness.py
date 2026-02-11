#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 file_listener.py 的容错能力

测试场景：
1. 正常 JSON 消息
2. 损坏的 JSON（缺少括号、非法字符）
3. 空行
4. 超长消息
5. 特殊字符（Unicode、控制字符）
6. 文件被删除后重新创建
"""

import os
import sys
import time
import json

MSG_FILE = os.path.join(os.environ.get('TEMP', '/tmp'), 'y3helper_messages.jsonl')

def write_msg(msg):
    """写入消息到文件"""
    with open(MSG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(f'[写入] {msg[:50]}...' if len(msg) > 50 else f'[写入] {msg}')

def run_test():
    print('=' * 60)
    print('file_listener.py 容错测试')
    print('=' * 60)
    print()
    print('请先在另一个终端启动: python file_listener.py')
    print('然后按 Enter 开始测试...')
    input()

    print('\n[测试1] 正常消息')
    write_msg(json.dumps({
        'type': 'print',
        'level': 'info',
        'message': '测试消息1：正常',
        'timestamp': '2024-01-01T00:00:00'
    }))
    time.sleep(0.5)

    print('\n[测试2] 损坏的 JSON（缺少闭合括号）')
    write_msg('{"type":"print","message":"测试消息2：损坏JSON"')
    time.sleep(0.5)

    print('\n[测试3] 完全非法的内容')
    write_msg('这不是JSON，只是纯文本!@#$%^&*()')
    time.sleep(0.5)

    print('\n[测试4] 空行')
    write_msg('')
    time.sleep(0.5)

    print('\n[测试5] 包含特殊字符的消息')
    write_msg(json.dumps({
        'type': 'print',
        'level': 'error',
        'message': '测试消息5：特殊字符 \n\t\r \\u0000 中文 🎉',
        'timestamp': '2024-01-01T00:00:05'
    }))
    time.sleep(0.5)

    print('\n[测试6] 超长消息（10000字符）')
    long_msg = 'A' * 10000
    write_msg(json.dumps({
        'type': 'print',
        'level': 'warn',
        'message': f'测试消息6：超长内容 {long_msg}',
        'timestamp': '2024-01-01T00:00:06'
    }))
    time.sleep(0.5)

    print('\n[测试7] 多行快速写入')
    for i in range(10):
        write_msg(json.dumps({
            'type': 'print',
            'level': 'debug',
            'message': f'测试消息7-{i}：快速写入',
            'timestamp': f'2024-01-01T00:00:{10+i:02d}'
        }))
    time.sleep(1)

    print('\n[测试8] 文件删除后重新创建')
    print('删除文件...')
    if os.path.exists(MSG_FILE):
        os.remove(MSG_FILE)
    time.sleep(1)
    print('重新创建并写入...')
    write_msg(json.dumps({
        'type': 'print',
        'level': 'info',
        'message': '测试消息8：文件重建后',
        'timestamp': '2024-01-01T00:01:00'
    }))
    time.sleep(0.5)

    print('\n[测试9] 错误级别消息')
    write_msg(json.dumps({
        'type': 'exception',
        'level': 'error',
        'message': '[EXCEPTION] attempt to call a nil value',
        'timestamp': '2024-01-01T00:01:10'
    }))
    time.sleep(0.5)

    print('\n[测试10] 心跳消息（应该被过滤）')
    write_msg(json.dumps({
        'type': 'print',
        'level': 'info',
        'message': '[HEARTBEAT] 1234567890',
        'timestamp': '2024-01-01T00:01:15'
    }))
    time.sleep(0.5)

    print('\n' + '=' * 60)
    print('测试完成！')
    print('=' * 60)
    print('\n检查 file_listener.py 输出：')
    print('  - 应该能看到所有正常消息')
    print('  - 损坏的 JSON 显示为 [RAW]')
    print('  - 心跳消息被过滤不显示')
    print('  - 没有因为错误而崩溃')
    print('\n如果 file_listener.py 仍在运行，说明容错成功！')

if __name__ == '__main__':
    run_test()
