@echo off
TITLE OpenClaw Intelligent System
color 0B

:: FORCE WORKING DIRECTORY TO SCRIPT LOCATION
cd /d "%~dp0"

echo ===================================================
echo       STARTING OPENCLAW INTELLIGENT SYSTEM
echo ===================================================
echo Working Directory: %CD%

:: 1. Activate Virtual Environment
:: Check parent dir first, then current dir
if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
) else (
    if exist ".venv\Scripts\activate.bat" (
        call ".venv\Scripts\activate.bat"
    )
)

:: 2. Start the TEACHER (Original System)
:: This is the live system handling current customers
echo [1/4] Starting TEACHER (Original AI Agent)...
start "FTS Teacher (New OpenClaw)" cmd /k "cd /d "%~dp0" && python ai_agent.py"

:: 3. Start the STUDENT (OpenClaw Core)
:: This is the new system learning from interactions
echo [2/4] Starting STUDENT (OpenClaw Core)...
start "OpenClaw Student" cmd /k "cd /d "%~dp0" && python OpenClaw_Core.py"

:: 4. Start the OBSERVER (The New Brain)
:: This monitors Airtable and analyzes context with AI
echo [3/4] Starting OBSERVER (Silent AI Context)...
start "OpenClaw Observer" cmd /k "cd /d "%~dp0" && python OpenClaw_Observer.py"

:: 5. Start Dashboard
:: To monitor logs from all systems
echo [4/4] Starting Live Dashboard...
start "FTS Live Dashboard" cmd /k "cd /d "%~dp0" && python dashboard.py"

echo.
echo ===================================================
echo       ALL SYSTEMS RUNNING
echo ===================================================
echo 1. Teacher (Old System) - Handling customers
echo 2. Student (OpenClaw Core) - Learning
echo 3. Observer (Airtable Brain) - Analyzing Workflow
echo 4. Dashboard (Monitoring) - Displaying Logs
echo.
pause
