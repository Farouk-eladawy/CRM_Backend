@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo FTS CRM - Install hourly GitHub backup
echo ========================================================
echo.
echo This creates a Windows Task Scheduler job that runs every hour.
echo main branch: project files + config + Gmail tokens + railway_vars.
echo Database zip: GitHub Release crm-data-latest (not Git).
echo First time only: run setup_github_release_backup.bat
echo It will NOT delete .git and will NOT force-push main.
echo.

where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    pause
    exit /b 1
)

if not exist "%~dp0.git" (
    echo [ERROR] This folder is not a git repository.
    echo The old deploy_to_github.bat used to destroy .git. That is no longer allowed.
    pause
    exit /b 1
)

schtasks /query /tn "FTS_Hourly_GitHub_Backup" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] Removing previous task FTS_Hourly_GitHub_Backup ...
    schtasks /delete /tn "FTS_Hourly_GitHub_Backup" /f >nul
)

echo [INFO] Creating hourly task...
schtasks /create /tn "FTS_Hourly_GitHub_Backup" /tr "\"%~dp0run_hourly_github_backup.bat\"" /sc HOURLY /mo 1 /f
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to create the scheduled task.
    echo Try running this file as the same Windows user that can git push.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Hourly GitHub backup is installed.
echo Task name: FTS_Hourly_GitHub_Backup
echo Log file:  hourly_github_backup.log
echo.
echo To run once now:
echo   run_hourly_github_backup.bat
echo.
echo To uninstall:
echo   schtasks /delete /tn "FTS_Hourly_GitHub_Backup" /f
echo.
pause
