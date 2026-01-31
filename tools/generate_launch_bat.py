#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动生成 launch_game.bat 脚本

读取项目配置并生成正确的启动脚本，无需手动填写路径。
"""

import os
from config import get_config

def generate_launch_bat():
    """生成 launch_game.bat"""
    config = get_config()

    if config['errors']:
        print('[错误] 配置检测失败:')
        for err in config['errors']:
            print(f'  - {err}')
        return False

    game_exe = config.get('game_exe')
    project_path = config.get('project_path')
    level_id = config.get('level_id')

    if not all([game_exe, project_path, level_id]):
        print('[错误] 缺少必要配置')
        return False

    game_dir = os.path.dirname(game_exe)

    # 生成 bat 内容
    content = f'''@echo off
chcp 65001 >nul
REM Y3 游戏启动脚本（自动生成，请勿手动修改）
REM 如需重新生成，运行: python generate_launch_bat.py

cd /d "{game_dir}"
start "" "Game_x64h.exe" --dx11 --start=Python "--python-args=type@editor_game,subtype@editor_game,editor_map_path@{project_path},level_id@{level_id},release@true,lua_dummy@space,lua_wait_debugger@true" --plugin-config=Plugins-PyQt --console --luaconsole
'''

    # 写入文件
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    bat_path = os.path.join(tools_dir, 'launch_game.bat')

    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print('[OK] launch_game.bat 已生成！')
    print(f'  路径: {bat_path}')
    print(f'  游戏目录: {game_dir}')
    print(f'  项目路径: {project_path}')
    print(f'  关卡 ID: {level_id}')
    print()
    print('[下一步] 以管理员身份运行 setup_launch_task.bat 创建计划任务')
    return True


if __name__ == '__main__':
    generate_launch_bat()
