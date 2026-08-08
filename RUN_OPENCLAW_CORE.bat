@echo off
TITLE OpenClaw Core System
color 0A

:: FORCE WORKING DIRECTORY TO SCRIPT LOCATION
cd /d "%~dp0"

echo ===================================================
echo       STARTING OPENCLAW CORE SYSTEM
echo ===================================================
echo Working Directory: %CD%

:: 1. Activate Virtual Environment
if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
) else (
    if exist ".venv\Scripts\activate.bat" (
        call ".venv\Scripts\activate.bat"
    )
)

:: 2. Start the OpenClaw Core
echo [1/1] Starting OpenClaw Core...
python OpenClaw_Core.py

pause
