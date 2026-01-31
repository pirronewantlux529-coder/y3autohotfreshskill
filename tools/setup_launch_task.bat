@echo off
chcp 65001 >nul
echo ===== Y3 Game Launcher Setup =====
echo Creating scheduled task for launching game without UAC popup...
echo Requires administrator privileges!
echo.

:: Get script directory
set SCRIPT_DIR=%~dp0

:: Check if launch_game.ps1 exists
if not exist "%SCRIPT_DIR%launch_game.ps1" (
    echo [ERROR] launch_game.ps1 not found in %SCRIPT_DIR%
    echo Please ensure all files are properly installed.
    pause
    exit /b 1
)

:: Create scheduled task for launching game (runs with highest privileges)
schtasks /create /tn "Y3LaunchGame" /tr "powershell -ExecutionPolicy Bypass -File \"%SCRIPT_DIR%launch_game.ps1\"" /sc once /st 00:00 /f /rl highest

if %errorlevel% equ 0 (
    echo.
    echo [OK] Scheduled task Y3LaunchGame created successfully!
    echo.
    echo Usage: python game_control.py launch
    echo.
    echo The game will start without UAC popup.
    echo Configuration is auto-detected from:
    echo   - .vscode/settings.json (Y3-Helper.EditorPath)
    echo   - header.project (entry_map.id)
) else (
    echo.
    echo [FAILED] Please run this script as Administrator
    echo Right-click and select "Run as administrator"
)

pause
