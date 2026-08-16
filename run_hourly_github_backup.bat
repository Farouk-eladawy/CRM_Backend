@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0hourly_github_backup.ps1"
exit /b %ERRORLEVEL%
