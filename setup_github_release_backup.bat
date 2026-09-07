@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo FTS CRM - One-time GitHub Release setup for DB zip
echo ========================================================
echo.
echo The database zip is larger than GitHub Git file limit (100MB).
echo It will be uploaded as Release "crm-data-latest" on:
echo   https://github.com/Farouk-eladawy/CRM_Backend/releases
echo.

set "GH_EXE=%~dp0tools\gh\gh.exe"

where gh >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "GH_EXE=gh"
    goto :AUTH
)

if exist "%GH_EXE%" goto :AUTH

echo [INFO] GitHub CLI not found. Downloading it directly...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_gh_cli.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Automatic download failed.
    echo Open https://cli.github.com/ , install GitHub CLI, then run this file again.
    pause
    exit /b 1
)

if not exist "%GH_EXE%" (
    echo [ERROR] gh.exe was not found after download.
    pause
    exit /b 1
)

:AUTH
echo [INFO] Checking GitHub login...
"%GH_EXE%" auth status
if %ERRORLEVEL% neq 0 (
    echo.
    echo [INFO] Login required. A browser window will open.
    "%GH_EXE%" auth login -s repo -w
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] GitHub login failed.
        pause
        exit /b 1
    )
)

echo.
echo [SUCCESS] GitHub CLI is ready.
echo Next: run run_hourly_github_backup.bat
echo After it finishes, open:
echo   https://github.com/Farouk-eladawy/CRM_Backend/releases
echo.
pause
