@echo off
REM Run notify_runner.py with event argument
set SCRIPT_PATH=C:\notify\notify_runner.py

if "%1"=="" (
    set EVENT_NAME=Startup/Login
) else (
    set EVENT_NAME=%1
)

cd /d C:\notify
python "%SCRIPT_PATH%" "%EVENT_NAME%"

exit