#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置管理模块 - 自动从项目文件检测配置

自动读取:
1. .vscode/settings.json 中的 Y3-Helper.EditorPath -> 游戏路径
2. header.project 中的 entry_map.id -> level_id
3. 从 tools 目录位置推断 script 和 project 路径

无需手动配置！
"""

import os
import json


def detect_script_path():
    """从当前 tools 目录推断 script 路径"""
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.dirname(tools_dir)
    if os.path.exists(os.path.join(script_path, 'main.lua')):
        return script_path
    return None


def detect_project_path(script_path):
    """从 script 路径推断项目路径

    script 路径: <project>/maps/<map_name>/script
    项目路径: <project>
    """
    if not script_path:
        return None
    parts = os.path.normpath(script_path).split(os.sep)
    try:
        maps_idx = parts.index('maps')
        return os.sep.join(parts[:maps_idx])
    except ValueError:
        return None


def read_y3_helper_config(script_path):
    """从 .vscode/settings.json 读取 Y3 Helper 配置"""
    if not script_path:
        return None
    vscode_settings = os.path.join(script_path, '.vscode', 'settings.json')
    if os.path.exists(vscode_settings):
        try:
            with open(vscode_settings, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings.get('Y3-Helper.EditorPath')
        except:
            pass
    return None


def read_header_project(project_path):
    """从 header.project 读取项目信息"""
    if not project_path:
        return None
    header_file = os.path.join(project_path, 'header.project')
    if os.path.exists(header_file):
        try:
            with open(header_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'level_id': str(data.get('entry_map', {}).get('id', '')),
                    'project_name': data.get('project_name', ''),
                }
        except:
            pass
    return None


def get_game_exe_from_editor(editor_path):
    """从编辑器路径推算游戏可执行文件路径

    Editor.exe 在: <y3>/games/2.0/game/Editor.exe
    Game_x64h.exe 在: <y3>/games/2.0/game/Engine/Binaries/Win64/Game_x64h.exe
    """
    if not editor_path:
        return None

    editor_dir = os.path.dirname(editor_path)  # .../game
    game_exe = os.path.join(editor_dir, 'Engine', 'Binaries', 'Win64', 'Game_x64h.exe')

    if os.path.exists(game_exe):
        return game_exe
    return None


def auto_detect_config():
    """自动检测所有配置

    Returns:
        dict: 配置字典
    """
    config = {
        'script_path': None,
        'project_path': None,
        'level_id': None,
        'game_exe': None,
        'editor_path': None,
        'errors': [],
    }

    # 1. 检测 script 路径
    script_path = detect_script_path()
    if not script_path:
        config['errors'].append('无法检测 script 路径（找不到 main.lua）')
        config['errors'].append('')
        config['errors'].append('tools 目录必须位于: <项目>/maps/<地图>/script/tools/')
        config['errors'].append('正确结构:')
        config['errors'].append('  你的项目/')
        config['errors'].append('    maps/')
        config['errors'].append('      地图名/')
        config['errors'].append('        script/')
        config['errors'].append('          main.lua    <-- 必须存在')
        config['errors'].append('          tools/      <-- 你应该在这里')
        config['errors'].append('            config.py')
        config['errors'].append('')
        config['errors'].append('请将整个 tools 文件夹复制到正确位置后重试')
        return config
    config['script_path'] = script_path

    # 2. 推断项目路径
    project_path = detect_project_path(script_path)
    if not project_path:
        config['errors'].append('无法从 script 路径推断项目路径')
        return config
    config['project_path'] = project_path

    # 3. 从 header.project 读取 level_id
    header_info = read_header_project(project_path)
    if header_info and header_info.get('level_id'):
        config['level_id'] = header_info['level_id']
    else:
        config['errors'].append('无法从 header.project 读取 level_id')

    # 4. 从 .vscode/settings.json 读取编辑器路径
    editor_path = read_y3_helper_config(script_path)
    if editor_path:
        config['editor_path'] = editor_path
        game_exe = get_game_exe_from_editor(editor_path)
        if game_exe:
            config['game_exe'] = game_exe
        else:
            config['errors'].append('从编辑器路径无法找到 Game_x64h.exe')
    else:
        config['errors'].append('无法从 .vscode/settings.json 读取 Y3-Helper.EditorPath')
        config['errors'].append('请在 VSCode/Cursor 中打开项目，Y3 Helper 会自动写入此配置')

    return config


def get_config():
    """获取配置（自动检测）"""
    return auto_detect_config()


def get_game_args(config, debug=False):
    """根据配置生成游戏启动参数"""
    if not config.get('project_path') or not config.get('level_id'):
        return []

    project_path = config['project_path'].replace('\\', '\\\\')
    level_id = config['level_id']
    wait_debugger = 'true' if debug else 'false'

    return [
        '--dx11',
        '--start=Python',
        f'--python-args=type@editor_game,subtype@editor_game,editor_map_path@{project_path},level_id@{level_id},release@true,lua_dummy@space,lua_wait_debugger@{wait_debugger}',
        '--plugin-config=Plugins-PyQt',
        '--console',
        '--luaconsole'
    ]


def print_config():
    """打印当前配置"""
    config = auto_detect_config()

    print('=' * 50)
    print('Y3 游戏控制工具 - 自动检测配置')
    print('=' * 50)
    print()

    items = [
        ('脚本路径', config.get('script_path')),
        ('项目路径', config.get('project_path')),
        ('关卡 ID', config.get('level_id')),
        ('编辑器路径', config.get('editor_path')),
        ('游戏可执行文件', config.get('game_exe')),
    ]

    for name, value in items:
        status = '[OK]' if value else '[!!]'
        print(f'{status} {name}: {value or "未检测到"}')

    if config['errors']:
        print()
        print('[警告] 问题:')
        for err in config['errors']:
            print(f'  - {err}')
    else:
        print()
        print('[OK] 所有配置检测成功!')

    return config


if __name__ == '__main__':
    print_config()
