#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Y3 Helper runLua 命令安装脚本
为 Y3 Helper 插件添加 runLua 命令，允许通过 Python 执行任意 Lua 代码

用法：
    # Windows
    python install_y3helper_runlua.py

    # WSL (需要用 Windows Python)
    /mnt/c/Windows/py.exe install_y3helper_runlua.py

安装后需要重启 VSCode/Cursor
"""
import os
import sys

def find_extension():
    """查找 Y3 Helper 插件路径"""
    possible_bases = []

    if sys.platform == 'win32':
        user_home = os.path.expanduser("~")
        possible_bases.extend([
            os.path.join(user_home, ".cursor", "extensions"),
            os.path.join(user_home, ".vscode", "extensions"),
        ])
        for user in ["Administrator", "Public"]:
            for drive in ["C:", "D:"]:
                base = os.path.join(drive, "Users", user)
                if os.path.exists(base):
                    possible_bases.append(os.path.join(base, ".cursor", "extensions"))
                    possible_bases.append(os.path.join(base, ".vscode", "extensions"))
    else:
        # WSL
        for drive in ["/mnt/c", "/mnt/d"]:
            if os.path.exists(drive):
                users_dir = os.path.join(drive, "Users")
                if os.path.exists(users_dir):
                    try:
                        for user in os.listdir(users_dir):
                            user_path = os.path.join(users_dir, user)
                            if os.path.isdir(user_path):
                                possible_bases.append(os.path.join(user_path, ".cursor", "extensions"))
                                possible_bases.append(os.path.join(user_path, ".vscode", "extensions"))
                    except:
                        pass

    for base in possible_bases:
        if os.path.exists(base):
            try:
                for name in os.listdir(base):
                    if name.startswith("sumneko.y3-helper"):
                        ext_path = os.path.join(base, name, "dist", "extension.js")
                        if os.path.exists(ext_path):
                            return ext_path
            except:
                continue

    return None

def install_runlua(ext_path):
    """安装 runLua 命令"""
    print(f"[INFO] 找到插件: {ext_path}")

    with open(ext_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'y3-helper.runLua' in content:
        print("[OK] runLua 命令已存在，无需重复安装")
        return True

    backup_path = ext_path + '.backup'
    if not os.path.exists(backup_path):
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[INFO] 已备份到: {backup_path}")

    old_code = 'a.commands.registerCommand("y3-helper.reloadLua",(async()=>{for(let e of g.allClients)e.notify("command",{data:".rd"})}))'
    new_code = old_code + ',a.commands.registerCommand("y3-helper.runLua",(async(code)=>{for(let e of g.allClients)e.notify("command",{data:code})}))'

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(ext_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[OK] runLua 命令安装成功！")
        print("")
        print("=" * 50)
        print("请重启 VSCode/Cursor 使修改生效")
        print("=" * 50)
        return True
    else:
        print("[ERROR] 找不到 reloadLua 命令，可能插件版本不兼容")
        return False

def main():
    print("=" * 50)
    print("Y3 Helper runLua 命令安装工具")
    print("=" * 50)
    print("")

    ext_path = find_extension()

    if not ext_path:
        print("[ERROR] 找不到 Y3 Helper 插件")
        print("请确认已安装 Y3 Helper 插件 (sumneko.y3-helper)")
        return 1

    return 0 if install_runlua(ext_path) else 1

if __name__ == '__main__':
    sys.exit(main())
