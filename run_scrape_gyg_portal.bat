@echo off
chcp 65001 > nul
title GYG Portal Scraper - FTS Travels
cd /d "%~dp0"

echo ============================================================
echo   GYG Supplier Portal Scraper (Edge - stable session)
echo ============================================================
echo.
echo BEFORE YOU START:
echo   1. CLOSE all GYG supplier tabs (including Cursor browser)
echo   2. Ensure gyg_portal_credentials.json exists with email/password/totp
echo   3. Do NOT close Edge until you see "Finished"
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

python -c "import json; d=json.load(open('gyg_portal_catalog.json',encoding='utf-8')); p=d.get('products',[]); n=len(p); dl=sum(1 for x in p if x.get('details_loaded')); sl=sum(1 for x in p if x.get('schedules_loaded')); print('Catalog status:'); print('  Product details loaded : %s/%s' % (dl, n)); print('  Schedules/pricing loaded: %s/%s' % (sl, n)); print('')"
if %errorlevel% neq 0 (
    echo [WARN] Could not read gyg_portal_catalog.json
    echo.
)

echo Choose scrape mode:
echo   1 = Missing product details only (default - skips if all 22 loaded)
echo   2 = Schedules + pricing (Show schedules)  ^<-- use this next
echo   3 = Re-enrich ALL products (details + inclusions)
echo   4 = Missing inclusions only
echo   5 = Re-scrape ALL products from scratch
echo   0 = Cancel
echo.
set /p MODE="Enter choice [2]: "
if "%MODE%"=="" set MODE=2
if "%MODE%"=="0" exit /b 0
if "%MODE%"=="1" (
    set ARGS=
    echo.
    echo Running: scrape missing product details...
)
if "%MODE%"=="2" (
    set ARGS=--schedules
    echo.
    echo Running: scrape schedules + pricing for all products...
)
if "%MODE%"=="3" (
    set ARGS=--enrich
    echo.
    echo Running: full enrich all 22 products...
)
if "%MODE%"=="4" (
    set ARGS=--missing-inclusions
    echo.
    echo Running: missing inclusions only...
)
if "%MODE%"=="5" (
    set ARGS=--all
    echo.
    echo Running: re-scrape ALL products...
)
if not defined ARGS (
    echo Invalid choice.
    pause
    exit /b 1
)

python scrape_gyg_portal.py %ARGS%
echo.
echo Done. Check gyg_portal_catalog.json and gyg_products.json
pause
