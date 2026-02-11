#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用 lua_executor 的测试示例

演示如何使用 lua_executor 模块进行可靠的游戏测试
"""

import os
import sys
import time

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lua_executor import execute_lua, execute_lua_file, print_result


def example_simple_test():
    """示例1：简单的Lua代码执行"""
    print('\n=== 示例1: 执行简单的Lua代码 ===')

    result = execute_lua("print('[测试] 简单打印')")
    print_result(result)

    return result.success


def example_with_error():
    """示例2：执行会报错的代码（演示错误捕获）"""
    print('\n=== 示例2: 执行有错误的代码 ===')

    # 故意调用一个不存在的函数
    result = execute_lua("nonexistent_function()")
    print_result(result)

    # 可以检查具体错误
    if not result.success:
        print(f'\n[分析] 检测到错误:')
        print(f'  游戏是否响应: {"是" if result.executed else "否"}')
        print(f'  游戏是否存活: {"是" if result.alive else "否"}')
        print(f'  日志错误数: {len(result.log_errors)}')
        print(f'  异常数: {len(result.exceptions)}')

    return result.success


def example_test_script():
    """示例3：执行tools目录下的测试脚本"""
    print('\n=== 示例3: 执行测试脚本 ===')

    # 执行 tools/pet_test.lua
    result = execute_lua_file('pet_test')
    print_result(result)

    return result.success


def example_multi_step_test():
    """示例4：多步骤测试（每步都检查）"""
    print('\n=== 示例4: 多步骤测试流程 ===')

    steps = [
        ("初始化测试", "print('[测试] 步骤1: 初始化')"),
        ("获取玩家", "local p = y3.player(1); print('[测试] 玩家:', p)"),
        ("获取存档", "local p = y3.player(1); local s = p:get_current_save(); print('[测试] 存档:', s)"),
    ]

    for i, (desc, code) in enumerate(steps, 1):
        print(f'\n[步骤 {i}] {desc}')
        result = execute_lua(code)

        if not result.success:
            print(f'✗ 步骤{i}失败: {result.error}')
            print_result(result, verbose=True)
            return False

        print(f'✓ 步骤{i}成功')
        time.sleep(0.5)  # 每步之间稍作停顿

    print('\n[完成] 所有步骤执行成功！')
    return True


def example_with_recovery():
    """示例5：演示自动恢复机制"""
    print('\n=== 示例5: 自动恢复机制 ===')

    # 这段代码会触发引擎异常（调用nil值）
    # lua_executor 会自动尝试 continue 恢复
    code = """
        local bad_value = nil
        bad_value()  -- 这会触发异常
    """

    result = execute_lua(code, auto_recover=True)
    print_result(result, verbose=True)

    if result.alive:
        print('\n[恢复] 游戏已从异常中恢复，可以继续测试')
        return True
    else:
        print('\n[失败] 游戏无法恢复，需要重启')
        return False


def main():
    """主测试流程"""
    print('=' * 60)
    print('lua_executor 测试示例')
    print('=' * 60)

    # 可以选择运行哪些示例
    examples = [
        ('简单测试', example_simple_test),
        ('错误捕获', example_with_error),
        ('测试脚本', example_test_script),
        ('多步骤测试', example_multi_step_test),
        ('自动恢复', example_with_recovery),
    ]

    if len(sys.argv) > 1:
        # 运行指定的示例
        index = int(sys.argv[1]) - 1
        if 0 <= index < len(examples):
            name, func = examples[index]
            print(f'\n运行示例: {name}')
            success = func()
            sys.exit(0 if success else 1)
        else:
            print(f'[错误] 示例编号必须在 1-{len(examples)} 之间')
            sys.exit(1)
    else:
        # 列出所有示例
        print('\n可用示例:')
        for i, (name, _) in enumerate(examples, 1):
            print(f'  {i}. {name}')
        print(f'\n用法: python {os.path.basename(__file__)} <编号>')
        print('示例: python test_with_executor.py 1')


if __name__ == '__main__':
    main()
