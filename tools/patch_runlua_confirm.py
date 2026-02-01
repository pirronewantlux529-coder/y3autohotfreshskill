#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Y3 Helper 补丁 - 为 runLua 命令添加执行确认

修改前：runLua 使用 notify（无响应）
修改后：runLua 使用 request（有响应，带超时）

这样可以知道命令是否真正执行成功。
"""

import os
import glob
import re
import shutil
from datetime import datetime


def find_y3_helper():
    """查找 Y3 Helper 插件路径"""
    user_home = os.path.expanduser("~")

    for editor in ["cursor", "vscode"]:
        ext_base = os.path.join(user_home, f".{editor}", "extensions")
        paths = glob.glob(os.path.join(ext_base, "sumneko.y3-helper-*"))
        if paths:
            return sorted(paths)[-1]

    return None


def patch_extension(ext_path):
    """应用补丁"""
    ext_js = os.path.join(ext_path, "dist", "extension.js")

    if not os.path.exists(ext_js):
        print(f"[错误] 找不到 extension.js: {ext_js}")
        return False

    # 备份
    backup_name = f"extension.js.backup.runlua_confirm.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = os.path.join(ext_path, "dist", backup_name)
    shutil.copy2(ext_js, backup_path)
    print(f"[备份] {backup_name}")

    # 读取内容
    with open(ext_js, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经打过补丁
    if 'RUNLUA_WITH_CONFIRM' in content:
        print("[提示] 补丁已经应用过了")
        return True

    # 原始代码模式
    # a.commands.registerCommand("y3-helper.runLua",(async(code)=>{for(let e of g.allClients)e.notify("command",{data:code})}))

    old_pattern = r'(registerCommand\("y3-helper\.runLua",\(async\(code\)=>\{for\(let e of )([a-zA-Z]+)(\.allClients\))e\.notify\("command",\{data:code\}\)\}\)\)'

    # 新代码：使用 request 并等待响应，添加超时处理
    # 注意：需要返回结果给调用者
    new_code = r'''registerCommand("y3-helper.runLua",(async(code)=>{/* RUNLUA_WITH_CONFIRM */const results=[];const timeout=5000;for(let e of \2\3{try{const result=await Promise.race([e.request("command",{data:code}),new Promise((_,reject)=>setTimeout(()=>reject(new Error("timeout")),timeout))]);results.push({success:true,result})}catch(err){results.push({success:false,error:err.message})}}return results}))'''

    new_content, count = re.subn(old_pattern, new_code, content)

    if count == 0:
        print("[错误] 未找到匹配的代码模式，可能插件版本不兼容")
        print("[提示] 尝试手动查找 'y3-helper.runLua' 相关代码")

        # 显示当前的代码片段帮助调试
        match = re.search(r'.{30}y3-helper\.runLua.{200}', content)
        if match:
            print(f"\n当前代码片段:\n{match.group()}")
        return False

    # 写入修改
    with open(ext_js, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"[成功] runLua 命令确认补丁已应用")
    print(f"[提示] 请重启 Cursor/VSCode 使补丁生效")
    return True


def main():
    print("Y3 Helper - runLua 命令确认补丁")
    print("=" * 50)

    ext_path = find_y3_helper()
    if not ext_path:
        print("[错误] 未找到 Y3 Helper 插件")
        print("[提示] 请先在 Cursor/VSCode 中安装 Y3 Helper")
        return

    print(f"[找到] {ext_path}")

    if patch_extension(ext_path):
        print()
        print("补丁说明：")
        print("  - runLua 命令现在会等待游戏响应")
        print("  - 超时时间：5秒")
        print("  - 返回值包含执行结果或错误信息")


if __name__ == '__main__':
    main()
