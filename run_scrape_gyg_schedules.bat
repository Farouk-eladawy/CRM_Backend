@echo off
chcp 65001 > nul
title GYG Schedules Scraper - FTS Travels
cd /d "%~dp0"
echo Scraping Show schedules + pricing for all products...
python scrape_gyg_portal.py --schedules
echo.
pause
