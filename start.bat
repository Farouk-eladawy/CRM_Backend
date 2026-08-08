@echo off
cd /d "%~dp0"
:: Activate virtual environment silently
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat" >nul 2>&1
)
:: Start the server in a new minimal window
start "FTS_AI_AGENT" /MIN python ai_agent.py
echo Server PID:
wmic process where "name='python.exe' and CommandLine like '%%ai_agent%%'" get ProcessId /format:csv 2>nul | findstr /v "ProcessId"
exit /b 0
