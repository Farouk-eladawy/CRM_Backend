@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo FTS Travels CRM - Railway CODE deploy only
echo Target Project: dazzling-amazement
echo Local CRM can stay RUNNING
echo ========================================================
echo.

cd /d "%~dp0"

where railway >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Railway CLI is not installed.
    echo Install: npm install -g @railway/cli
    pause
    exit /b 1
)

echo [INFO] Checking Railway login...
call railway whoami >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Opening browser for Railway login...
    call railway login
) else (
    echo [INFO] Already logged in.
)

echo.
echo [INFO] Linking project dazzling-amazement ...
call railway link
if %ERRORLEVEL% neq 0 (
    echo [ERROR] railway link failed.
    pause
    exit /b 1
)

echo.
echo [INFO] Deploying code with railway up --detach ...
call railway up --detach
if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Code upload started.
    echo Check Railway Dashboard build logs.
    echo.
    echo Next recommended command:
    echo   prepare_railway_staging.bat
) else (
    echo.
    echo [ERROR] Deployment failed. Check logs above.
)

pause
