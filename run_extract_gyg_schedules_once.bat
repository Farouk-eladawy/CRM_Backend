@echo off
chcp 65001 > nul
title GYG One-Time Schedule Extract - FTS Travels
cd /d "%~dp0"
echo Extracting schedules + pricing for all 22 products...
python extract_gyg_schedules_once.py
echo.
pause
