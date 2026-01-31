#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置管理模块 - 自动从项目文件检测配置

自动读取:
1. .vscode/settings.json 中的 Y3-Helper.EditorPath -> 游戏路径
2. header.project 中的 entry_map.id -> level_id
3. 从 tools 目录位置推断 script 和 project 路径

如果自动检测失败，支持用户提供路径进行模糊搜索。
"""

import os
import json
import glob


# 配置文件路径（保存用户手动指定的路径）
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.user_config.json')


def find_script_dirs(search_path, max_depth=5):
    """在指定路径下搜索包含 main.lua 的 script 目录

    Args:
        search_path: 搜索起始路径
        max_depth: 最大搜索深度

    Returns:
        list: 找到的 script 目录列表
    """
    results = []
    search_path = os.path.abspath(search_path)

    # 使用 glob 模式搜索
    for depth in range(1, max_depth + 1):
        pattern = os.path.join(search_path, *(['*'] * depth), 'main.lua')
        for main_lua in glob.glob(pattern):
            script_dir = os.path.dirname(main_lua)
            # 验证是否是有效的 Y3 项目结构
            if 'maps' in script_dir and script_dir.endswith('script'):
                results.append(script_dir)

    return list(set(results))  # 去重


def save_user_config(script_path):
    """保存用户配置"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'script_path': script_path}, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


def load_user_config():
    """加载用户配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                script_path = data.get('script_path')
                if script_path and os.path.exists(os.path.join(script_path, 'main.lua')):
                    return script_path
        except:
            pass
    return None


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


def auto_detect_config(script_path_override=None):
    """自动检测所有配置

    Args:
        script_path_override: 手动指定的 script 路径（覆盖自动检测）

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

    # 1. 检测 script 路径（优先级：参数 > 自动检测 > 用户配置）
    script_path = script_path_override or detect_script_path() or load_user_config()

    if not script_path:
        config['errors'].append('无法检测 script 路径')
        config['errors'].append('')
        config['errors'].append('请运行: python config.py --search <你的Y3项目目录>')
        config['errors'].append('例如: python config.py --search D:\\Y3')
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


def print_config(config=None):
    """打印当前配置"""
    if config is None:
        config = auto_detect_config()

    print('=' * 50)
    print('Y3 游戏控制工具 - 配置检测')
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
            if err:
                print(f'  - {err}')
            else:
                print()
    else:
        print()
        print('[OK] 所有配置检测成功!')

    return config


def search_and_select(search_path):
    """搜索项目并让用户选择"""
    print(f'正在搜索: {search_path}')
    print('请稍候...')
    print()

    results = find_script_dirs(search_path)

    if not results:
        print('[!!] 未找到任何 Y3 项目')
        print()
        print('确保搜索路径下有 Y3 项目，结构如:')
        print('  <项目>/maps/<地图>/script/main.lua')
        return None

    print(f'找到 {len(results)} 个项目:')
    print()

    for i, path in enumerate(results, 1):
        # 提取项目名和地图名
        parts = path.split(os.sep)
        try:
            maps_idx = parts.index('maps')
            project_name = parts[maps_idx - 1] if maps_idx > 0 else '?'
            map_name = parts[maps_idx + 1] if maps_idx + 1 < len(parts) else '?'
            print(f'  [{i}] {project_name} / {map_name}')
            print(f'      {path}')
        except:
            print(f'  [{i}] {path}')
        print()

    if len(results) == 1:
        choice = 1
        print(f'只有一个项目，自动选择 [{choice}]')
    else:
        try:
            choice = int(input('请选择项目编号 (输入数字): '))
        except (ValueError, EOFError):
            print('取消选择')
            return None

    if 1 <= choice <= len(results):
        selected = results[choice - 1]
        print()
        print(f'已选择: {selected}')

        # 保存配置
        if save_user_config(selected):
            print('[OK] 配置已保存，下次自动使用此路径')

        return selected
    else:
        print('无效选择')
        return None


def main():
    """主函数"""
    import sys

    # 处理命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--search' and len(sys.argv) > 2:
            # 搜索模式
            search_path = sys.argv[2]
            if not os.path.exists(search_path):
                print(f'[!!] 路径不存在: {search_path}')
                return

            selected = search_and_select(search_path)
            if selected:
                print()
                print('=' * 50)
                config = auto_detect_config(selected)
                print_config(config)

        elif sys.argv[1] == '--clear':
            # 清除保存的配置
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
                print('[OK] 已清除保存的配置')
            else:
                print('没有保存的配置')

        elif sys.argv[1] == '--help':
            print('Y3 游戏配置检测工具')
            print()
            print('用法:')
            print('  python config.py              # 自动检测配置')
            print('  python config.py --search <路径>  # 搜索指定目录下的Y3项目')
            print('  python config.py --clear      # 清除保存的配置')
            print()
            print('示例:')
            print('  python config.py --search D:\\Y3')
            print('  python config.py --search C:\\Users\\你的用户名\\Documents')

        else:
            print(f'未知参数: {sys.argv[1]}')
            print('使用 --help 查看帮助')
    else:
        # 默认：自动检测
        print_config()


if __name__ == '__main__':
    main()
