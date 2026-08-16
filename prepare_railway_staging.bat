@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo FTS CRM - Railway STAGING prepare (local stays RUNNING)
echo ========================================================
echo.
echo This will:
echo  1) Create a safe DB snapshot (local CRM stays online)
echo  2) Deploy code to Railway
echo  3) Upload snapshot files to Railway Volume /app/data
echo.
echo IMPORTANT:
echo  - Do NOT switch Meta/WhatsApp webhooks yet
echo  - Local server remains the live production receiver
echo.
pause

cd /d "%~dp0"

where railway >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Railway CLI not found.
    echo Install: npm install -g @railway/cli
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
echo [1/4] Creating safe snapshot while local is running...
python snapshot_db_for_railway.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Snapshot failed.
    pause
    exit /b 1
)

echo.
echo [2/4] Checking Railway login...
call railway whoami >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Login required...
    call railway login
)

echo.
echo [3/4] Linking project then deploying CODE...
echo Select project: dazzling-amazement
call railway link
if %ERRORLEVEL% neq 0 (
    echo [ERROR] railway link failed.
    pause
    exit /b 1
)

call railway up --detach
if %ERRORLEVEL% neq 0 (
    echo [ERROR] railway up failed.
    pause
    exit /b 1
)

echo.
echo [4/4] Uploading snapshot files to Volume /app/data ...
if exist "railway_staging_upload\chat_history.db" (
    call railway volume upload "railway_staging_upload\chat_history.db" /app/data/chat_history.db
) else (
    echo [ERROR] chat_history.db snapshot missing.
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
echo [DONE] Staging upload finished. Local CRM is still live.
echo.
echo YOUR next steps are printed by: railway_user_test_checklist.bat
echo ========================================================
call "%~dp0railway_user_test_checklist.bat"
pause
