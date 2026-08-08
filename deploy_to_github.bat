@echo off
echo ========================================================
echo FTS Travels CRM - GitHub Direct Deployment Script
echo ========================================================
echo.

:: Check if git is installed
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git is not installed or not found in system PATH.
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)

:: Ensure we are in the correct directory
cd /d "%~dp0"

:: The ONLY way to fix a 4GB+ Git repository history is to destroy the .git folder
:: and start a completely fresh history. Since this is a new deployment to Railway,
:: we don't need the local commit history.
echo [WARNING] The repository history is too large (4GB+) for GitHub to accept.
echo [INFO] Destroying local git history to start fresh...
rmdir /s /q .git

:: Re-initialize fresh
echo [INFO] Initializing fresh Git repository...
git init

:: Setup the remote origin
echo [INFO] Configuring remote origin: https://github.com/Farouk-eladawy/CRM_Backend.git
git remote add origin https://github.com/Farouk-eladawy/CRM_Backend.git

:: Ensure we are on the main branch
git checkout -b main

:: Add all files (the new .gitignore will now correctly filter out the 4GB of junk)
echo [INFO] Staging files...
git add .

:: Commit the changes
echo [INFO] Committing changes...
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "commit_msg=Fresh Deployment: %datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%"
git commit -m "%commit_msg%"

:: Push to GitHub
echo [INFO] Pushing fresh code to GitHub (main branch)...
echo [NOTE] This will overwrite the remote repository history.
git push -u origin main --force

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================================
    echo [SUCCESS] Code has been successfully pushed to GitHub!
    echo If Railway is linked to this repo, it should start building now.
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo [ERROR] Failed to push code to GitHub. 
    echo Please check your internet connection or GitHub permissions.
    echo ========================================================
)

pause
