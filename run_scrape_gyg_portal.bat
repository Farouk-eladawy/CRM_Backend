@echo off
chcp 65001 > nul
title GYG Portal Scraper - FTS Travels
cd /d "%~dp0"

echo ============================================================
echo   GYG Supplier Portal Scraper (Firefox - stable session)
echo ============================================================
echo.
echo BEFORE YOU START:
echo   1. CLOSE all GYG supplier tabs (including Cursor browser)
echo   2. Copy gyg_portal_credentials.example.json to gyg_portal_credentials.json
echo      and fill email + password + totp_secret (same as scrape_gyg_supplier)
echo   3. Do NOT close Firefox until you see "Done"
echo.
echo Remaining trips to scrape: 11 of 22
echo Saves after EACH trip - safe to stop and rerun anytime.
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

python scrape_gyg_portal.py
echo.
pause
