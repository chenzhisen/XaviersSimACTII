@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: 设置颜色代码
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

:: 标题
title Xavier Simulation Runner

:: 创建错误日志文件
set "ERROR_LOG=error_log.txt"
if exist "%ERROR_LOG%" del "%ERROR_LOG%"

:: 将所有输出重定向到文件和控制台
(
    :: 打印标题
    echo %BLUE%=== Xavier Simulation Runner ===%RESET%
    echo.
    
    :: 检查 Python 安装
    echo %BLUE%检查 Python 安装...%RESET%

    :: 首先检查标准 Python 安装
    set "PYTHON_LOCATIONS=^
    C:\Python313\python.exe;^
    C:\Python312\python.exe;^
    C:\Python311\python.exe;^
    C:\Python310\python.exe;^
    C:\Python39\python.exe;^
    C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe;^
    C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe;^
    C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe;^
    C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe;^
    C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39\python.exe"

    :: 遍历可能的 Python 位置
    for %%p in (%PYTHON_LOCATIONS%) do (
        if exist "%%p" (
            set "PYTHON_PATH=%%p"
            goto :found_python
        )
    )

    :: 如果没找到标准安装，尝试使用 where 命令
    where python > nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=*" %%i in ('where python') do (
            set "PYTHON_PATH=%%i"
            :: 检查是否是 Microsoft Store 版本
            if "!PYTHON_PATH:WindowsApps=!"=="!PYTHON_PATH!" (
                goto :found_python
            ) else (
                echo %YELLOW%警告: 检测到 Microsoft Store 版本的 Python%RESET%
                echo %YELLOW%建议安装官方 Python（https://www.python.org/downloads/）%RESET%
                echo.
                goto :python_error
            )
        )
    )

    :python_error
    echo %RED%错误: 未找到合适的 Python 安装%RESET%
    echo %YELLOW%请访问 https://www.python.org/downloads/ 下载并安装 Python%RESET%
    echo %YELLOW%安装时请勾选 "Add Python to PATH"%RESET%
    pause
    exit /b 1

    :found_python
    echo %GREEN%- 找到 Python: %PYTHON_PATH%%RESET%

    :: 检查 Python 版本
    for /f "tokens=*" %%v in ('"%PYTHON_PATH%" -V') do (
        echo %GREEN%- Python 版本: %%v%RESET%
    )

    :: 检查 pip
    echo.
    echo %BLUE%检查 pip 安装...%RESET%
    "%PYTHON_PATH%" -m pip --version > nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%- pip 未安装，正在安装...%RESET%
        "%PYTHON_PATH%" -m ensurepip --upgrade --default-pip
        if errorlevel 1 (
            echo %RED%错误: pip 安装失败%RESET%
            echo %YELLOW%请尝试手动安装 pip:%RESET%
            echo %YELLOW%1. 下载 get-pip.py: https://bootstrap.pypa.io/get-pip.py%RESET%
            echo %YELLOW%2. 运行: python get-pip.py%RESET%
            pause
            exit /b 1
        )
    )
    echo %GREEN%- pip 安装正常%RESET%

    :: 检查必要的目录
    echo.
    echo %BLUE%创建必要的目录...%RESET%
    if not exist "logs\dev\tech" mkdir "logs\dev\tech"
    if not exist "logs\dev\tweets" mkdir "logs\dev\tweets"
    if not exist "data\dev" mkdir "data\dev"
    if not exist "data\prod" mkdir "data\prod"
    echo %GREEN%- 目录创建完成%RESET%

    :: 安装依赖
    echo.
    echo %BLUE%安装依赖包...%RESET%
    "%PYTHON_PATH%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo %RED%错误: 依赖安装失败%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%- 依赖安装成功%RESET%

    :: 设置 PYTHONPATH
    echo.
    echo %BLUE%设置环境变量...%RESET%
    set "PYTHONPATH=%~dp0"
    echo %GREEN%- PYTHONPATH: %PYTHONPATH%%RESET%

    :: 运行程序
    echo.
    echo %BLUE%启动 Xavier...%RESET%
    echo %YELLOW%按 Ctrl+C 可以终止程序%RESET%
    echo.

    :: 记录开始时间
    set "START_TIME=%TIME%"

    :: 运行 Python 脚本
    "%PYTHON_PATH%" run_xavier.py

    :: 检查运行结果
    if errorlevel 1 (
        echo.
        echo %RED%程序运行失败%RESET%
    ) else (
        echo.
        echo %GREEN%程序运行成功%RESET%
    )

    :: 计算运行时间
    set "END_TIME=%TIME%"
    set "START_H=%START_TIME:~0,2%"
    set "START_M=%START_TIME:~3,2%"
    set "START_S=%START_TIME:~6,2%"
    set "END_H=%END_TIME:~0,2%"
    set "END_M=%END_TIME:~3,2%"
    set "END_S=%END_TIME:~6,2%"

    :: 去除前导零
    set /a "START_H=1%START_H%-100"
    set /a "START_M=1%START_M%-100"
    set /a "START_S=1%START_S%-100"
    set /a "END_H=1%END_H%-100"
    set /a "END_M=1%END_M%-100"
    set /a "END_S=1%END_S%-100"

    :: 计算总秒数
    set /a "START_SECS=(%START_H%*3600)+(%START_M%*60)+%START_S%"
    set /a "END_SECS=(%END_H%*3600)+(%END_M%*60)+%END_S%"
    set /a "DIFF_SECS=%END_SECS%-%START_SECS%"

    :: 转换为时分秒
    set /a "DIFF_H=%DIFF_SECS%/3600"
    set /a "DIFF_M=(%DIFF_SECS%%%3600)/60"
    set /a "DIFF_S=%DIFF_SECS%%%60"

    echo %BLUE%运行时间: %DIFF_H%时%DIFF_M%分%DIFF_S%秒%RESET%
    echo.

    :: 运行结束
    echo.
    echo %BLUE%按任意键退出...%RESET%
    pause > nul
) > "%ERROR_LOG%" 2>&1

:: 如果发生错误，显示错误日志
if errorlevel 1 (
    cls
    echo %RED%运行出错！错误日志：%RESET%
    echo.
    type "%ERROR_LOG%"
    echo.
    echo %YELLOW%请查看上述错误信息，按任意键退出...%RESET%
    pause > nul
) else (
    :: 成功运行后删除错误日志
    if exist "%ERROR_LOG%" del "%ERROR_LOG%"
)

:: 确保窗口不会立即关闭
echo.
echo %BLUE%程序运行结束，按任意键退出...%RESET%
pause > nul 