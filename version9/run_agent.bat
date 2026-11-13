@echo off
title Command Center Launcher

:run_agent
cls
echo ==========================================
echo      COMMAND CENTER RECOVERY SYSTEM
echo ==========================================
echo Starting Latest Agent (main8.py)...
echo ==========================================

:: This runs your python script and waits for it to finish or crash
python main8.py

:: If main8.py crashes, the script reaches this point instead of closing
echo.
echo [!] Agent stopped or crashed! Restarting in 3 seconds...
timeout /t 3 >nul

:: Loops back to the top and starts it again
goto run_agent