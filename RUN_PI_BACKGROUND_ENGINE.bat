@echo off
title PI Background Task Engine
echo ====================================================
echo Starting PI Background Task Engine
echo This engine monitors PI outbox, watchers, and tasks.
echo ====================================================

:: Set working directory to the script's folder
cd /d "%~dp0"

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

:: Run the engine
set PYTHONPATH=%~dp0
python runtime\pi_brain\background_task_engine.py

pause