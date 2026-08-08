@echo off
title AI Agent Report Monitor
color 0A
cd /d "c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject"

:loop
cls
echo ============================================================
echo   AI AGENT SYSTEM MONITOR (Updates every 5 seconds)
echo   Current System Time: %date% %time%
echo ============================================================
echo.
echo   Latest Operation Log:
echo   ---------------------

if exist last_run_log.txt (
    type last_run_log.txt
) else (
    echo   [No logs found yet. Waiting for the first scheduled run...]
)

echo.
echo ============================================================
echo   Waiting for next scheduled task...
echo   (Morning: 08:05 AM | Evening: 02:05 PM | Night: 10:05 PM)
echo ============================================================

:: Alternative delay method using ping (more reliable than timeout)
ping 127.0.0.1 -n 6 >nul
goto loop

:: Prevent auto-close on error
pause
