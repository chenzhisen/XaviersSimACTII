@echo off
chcp 65001 > nul

:: 设置颜色代码
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

:: 显示启动信息
echo %BLUE%=== 启动 Xavier Simulation ===%RESET%
echo.
echo %YELLOW%程序将在新窗口中运行%RESET%
echo %YELLOW%请不要关闭命令行窗口%RESET%
echo.

:: 在新窗口中运行主脚本
start "Xavier Simulation" cmd /k "run_xavier.bat"

:: 等待用户确认退出
echo %BLUE%主程序已在新窗口启动%RESET%
echo %YELLOW%您可以关闭此窗口%RESET%
echo.
pause 