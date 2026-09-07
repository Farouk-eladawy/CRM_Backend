@echo off
echo ========================================================
echo FTS Travels CRM - Safe GitHub backup
echo ========================================================
echo.
echo The old version of this file deleted .git and force-pushed.
echo That is retired. This now runs the private hourly backup once:
echo   - main: code + config.json + Gmail tokens + railway_vars.json
echo   - DB zip: GitHub Release crm-data-latest
echo If gh is missing, run setup_github_release_backup.bat first.
echo.

cd /d "%~dp0"
call "%~dp0run_hourly_github_backup.bat"
echo.
echo Check hourly_github_backup.log if anything failed.
pause
