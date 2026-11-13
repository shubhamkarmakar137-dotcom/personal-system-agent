@echo off
title Command Center Launcher

:menu
cls
echo ==========================================
echo      COMMAND CENTER RECOVERY SYSTEM
echo ==========================================
echo [1] Start Latest Agent (main6.1.py)
echo [2] Start Stable Version (main6.py)
echo ==========================================
set /p choice="Select an option (1-2): "

if "%choice%"=="1" goto run_v6.1
if "%choice%"=="2" goto run_v6
goto menu

:run_v6.1
cls
echo Starting Command Center (Version 6.1)...
python main6.1.py

REM Check if Python crashed (Exit code is not 0)
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==========================================
    echo ⚠️ [CRASH DETECTED] Version 6.1 exited with a fatal error!
    echo ==========================================
    echo Your broken code in main6.1.py is safe and HAS NOT been overwritten.
    echo.
    set /p fallback="Do you want to run Version 6 instead so you can keep working? (Y/N): "
    
    if /I "%fallback%"=="Y" (
        goto run_v6
    )
)

echo.
pause
goto menu

:run_v6
cls
echo Starting Command Center (Version 6)...
if exist main6.py (
    python main6.py
) else (
    echo ❌ [ERROR] main6.py not found in the folder!
)

echo.
pause
goto menu