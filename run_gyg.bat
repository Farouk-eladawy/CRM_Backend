@echo off
chcp 65001 > nul
title FTS GYG AI Agent

echo ===================================================
echo     Starting GetYourGuide AI Auto-Reply Service
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python and try again.
    pause
    exit /b 1
)

:: Run the script in a loop to ensure it never dies
:loop
echo [%date% %time%] Starting gyg_service.py...
python gyg_service.py

echo.
echo [%date% %time%] Script finished or crashed.
echo Restarting in 10 seconds. Press CTRL+C to stop completely.
timeout /t 10 /nobreak > nul
goto loop
