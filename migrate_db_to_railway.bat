@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo FTS CRM - FINAL cutover DB upload (STOP local first)
echo ========================================================
echo.
echo Use this ONLY at cutover time:
echo  1) Stop local Windows CRM
echo  2) Run this script
echo  3) Point webhooks to Railway
echo  4) Point frontend API to Railway
echo.
echo If you are only TESTING, use prepare_railway_staging.bat instead.
echo.
pause

cd /d "%~dp0"

where railway >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Railway CLI not found. Run: npm install -g @railway/cli
    pause
    exit /b 1
)

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH.
    pause
    exit /b 1
)

echo.
echo [INFO] Creating final snapshot from local files...
python snapshot_db_for_railway.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Snapshot failed.
    pause
    exit /b 1
)

echo.
echo [INFO] Linking Railway project...
call railway link

echo.
echo [INFO] Uploading FINAL data to /app/data ...
if not exist "railway_staging_upload\chat_history.db" (
    echo [ERROR] Missing snapshot chat_history.db
    pause
    exit /b 1
)

call railway volume upload "railway_staging_upload\chat_history.db" /app/data/chat_history.db
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed uploading chat_history.db
    pause
    exit /b 1
)

if exist "railway_staging_upload\learned_corrections.json" (
    call railway volume upload "railway_staging_upload\learned_corrections.json" /app/data/learned_corrections.json
)

for %%F in (
    hajj_tahseen_followup_state.json
    religious_15day_followup_state.json
    religious_umrah_8day_followup_state.json
    religious_umrah_10day_followup_state.json
    religious_hajj_earlybooking_followup_state.json
    sales_reminder_state.json
) do (
    if exist "railway_staging_upload\%%F" (
        echo Uploading %%F ...
        call railway volume upload "railway_staging_upload\%%F" /app/data/%%F
    )
)

echo.
echo ========================================================
echo [DONE] Final DB upload complete.
echo NEXT:
echo  1) Restart Railway service from dashboard
echo  2) Switch WhatsApp/Facebook/Email webhooks to Railway URL
echo  3) Point frontend VITE_API_BASE to Railway API
echo  4) Keep local OFF for 24-48h as rollback backup
echo ========================================================
pause
