@echo off
title Airtable Phone Corrector (Runs every 10 mins)
cd /d "%~dp0"

:loop
cls
echo ========================================================
echo Running Phone Correction Script...
echo Time: %TIME%
echo ========================================================

REM Run the script using the virtual environment python
"..\.venv\Scripts\python.exe" phone_corrector.py

echo.
echo Done. Waiting 10 minutes before next run...
echo Press CTRL+C to stop.
timeout /t 600
goto loop
