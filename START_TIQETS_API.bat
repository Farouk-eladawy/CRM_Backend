@echo off
cd /d "%~dp0"
echo Starting Tiqets Supplier API on port 5005...
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat" >nul 2>&1
start "TIQETS_API_5005" python tiqets_api.py
echo Open another window and run: python tools\tiqets_connectivity_check.py
pause
