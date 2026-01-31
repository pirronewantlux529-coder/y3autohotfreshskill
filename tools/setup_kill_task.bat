@echo off
chcp 65001 >nul
echo 创建杀游戏进程的计划任务...
echo 需要管理员权限运行此脚本

:: 获取脚本目录
set SCRIPT_DIR=%~dp0

:: 创建计划任务用于杀游戏进程（只杀有console子进程的，不杀编辑器）
schtasks /create /tn "Y3KillGame" /tr "powershell -ExecutionPolicy Bypass -File \"%SCRIPT_DIR%kill_game.ps1\"" /sc once /st 00:00 /f /rl highest

if %errorlevel% equ 0 (
    echo.
    echo [成功] 计划任务 Y3KillGame 已创建
    echo 使用方法: python game_control.py kill
    echo 注意: 只会杀掉游戏进程，不会杀编辑器
) else (
    echo.
    echo [失败] 请以管理员身份运行此脚本
)

pause
