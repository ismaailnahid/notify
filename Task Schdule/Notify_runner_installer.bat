@echo off
setlocal enabledelayedexpansion

:: Administrator privilege check
NET FILE 1>NUL 2>NUL
if '%errorlevel%' == '0' (
    echo Administrator privileges confirmed.
) else (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c %0' -Verb RunAs"
    exit /b
)

echo ========================================
echo    PC Notify System Installer
echo ========================================
echo.

set INSTALL_DIR=C:\notify
set SCRIPT_DIR=%~dp0

:: Create directory and copy files
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
echo Copying files...
copy "%SCRIPT_DIR%notify_runner.py" "%INSTALL_DIR%\"
copy "%SCRIPT_DIR%notifu_runner.bat" "%INSTALL_DIR%\notify_runner.bat"

:: Install Python packages
echo Installing Python packages...
python -m pip install opencv-python psutil requests

echo.
echo Removing existing tasks...
schtasks /Delete /TN "Notify - Startup" /F 2>nul
schtasks /Delete /TN "Notify - Shutdown" /F 2>nul
schtasks /Delete /TN "Notify Wakeup" /F 2>nul
schtasks /Delete /TN "Notify Sleep Hibernate" /F 2>nul

echo Creating new tasks...

:: 1. Startup Task (Logon)
schtasks /Create /TN "Notify - Startup" /TR "C:\notify\notify_runner.bat Startup/Login" /SC ONLOGON /RL HIGHEST /F
echo ✓ Startup task created

:: 2. Shutdown Task (Event 1074)
schtasks /Create /TN "Notify - Shutdown" /TR "C:\notify\notify_runner.bat Shutdown" /SC ONEVENT /EC System /MO "*[System[EventID=1074]]" /F
echo ✓ Shutdown task created

:: 3. Wakeup Task (Event ID 1 from Kernel-Power)
schtasks /Create /TN "Notify Wakeup" /TR "C:\notify\notify_runner.bat Wakeup" /SC ONEVENT /EC System /MO "*[System[Provider[@Name='Microsoft-Windows-Kernel-Power'] and EventID=1]]" /F
echo ✓ Wakeup task created

:: 4. Sleep/Hibernate Task (Event ID 42 from Kernel-Power)
schtasks /Create /TN "Notify Sleep Hibernate" /TR "C:\notify\notify_runner.bat Sleep" /SC ONEVENT /EC System /MO "*[System[Provider[@Name='Microsoft-Windows-Kernel-Power'] and EventID=42]]" /F
echo ✓ Sleep/Hibernate task created

echo.
echo ========================================
echo    Installation Completed Successfully!
echo ========================================
echo.
echo Verifying tasks...
echo.
schtasks /Query /TN "Notify - Startup" /FO LIST 2>nul | find "TaskName" && echo • Notify - Startup - ✓ INSTALLED
schtasks /Query /TN "Notify - Shutdown" /FO LIST 2>nul | find "TaskName" && echo • Notify - Shutdown - ✓ INSTALLED
schtasks /Query /TN "Notify Wakeup" /FO LIST 2>nul | find "TaskName" && echo • Notify Wakeup - ✓ INSTALLED
schtasks /Query /TN "Notify Sleep Hibernate" /FO LIST 2>nul | find "TaskName" && echo • Notify Sleep Hibernate - ✓ INSTALLED

echo.
echo Testing script...
cd /d "%INSTALL_DIR%"
notify_runner.bat "Test"

echo.
pause