@echo off
setlocal enabledelayedexpansion

:: Debug line - will show in system logs
echo Xavier cron job started at %date% %time% >> %TEMP%\xavier_debug.log

:: Set script directory to current location
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Set PYTHONPATH to include the project root directory
set "PYTHONPATH=%SCRIPT_DIR%"

:: Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

:: Create log file with date
set "LOG_FILE=logs\cron_xavier_%date:~10,4%%date:~4,2%%date:~7,2%.log"

echo === Run started at %date% %time% === >> "%LOG_FILE%"

:: Run the Python script
py -m src.main --provider xai --is-production >> "%LOG_FILE%" 2>&1
set RESULT=%ERRORLEVEL%

echo Python script exit code: %RESULT% >> "%LOG_FILE%"
echo === Run completed at %date% %time% === >> "%LOG_FILE%"

endlocal 