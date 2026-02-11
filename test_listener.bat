@echo off
chcp 65001 >nul
echo ====================================
echo file_listener.py 容错测试
echo ====================================
echo.
echo 即将启动两个窗口：
echo 1. 监听器窗口 (file_listener.py)
echo 2. 测试脚本窗口 (test_listener_robustness.py)
echo.
echo 请观察监听器是否能处理所有异常情况而不崩溃
echo.
pause

cd tools

rem 启动监听器
start "file_listener" cmd /k "python file_listener.py"

rem 等待监听器启动
timeout /t 2 /nobreak >nul

rem 启动测试脚本
start "测试脚本" cmd /k "python test_listener_robustness.py"

echo.
echo 两个窗口已启动，请查看测试结果
pause
