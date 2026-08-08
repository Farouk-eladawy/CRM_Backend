@echo off
title Upload New Frontend Dashboard
echo ===================================================
echo Uploading new_frontend_dashboard to GitHub
echo ===================================================

cd /d "c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\frontend_dashboard\new_frontend_dashboard"

echo.
echo [1] Initializing Git repository...
if not exist .git (
    git init
    git branch -M main
)

echo.
echo [2] Setting up remote repository (Origin)...
git remote remove origin 2>nul
git remote add origin https://github.com/Farouk-eladawy/FTS_AI_CRM.git

echo.
echo [3] Adding all files...
git add .

echo.
echo [4] Committing changes...
set /p commit_msg="Enter commit message (or press Enter for default 'Update frontend dashboard'): "
if "%commit_msg%"=="" set commit_msg=Update frontend dashboard
git commit -m "%commit_msg%"

echo.
echo [5] Pushing to GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo ===================================================
    echo [WARNING] An error occurred during push. 
    echo This usually happens if the remote repository has files you don't have locally.
    echo Press 1 to Pull changes first, then Push.
    echo Press 2 to Force Push (WARNING: Overwrites remote files).
    echo Press any other key to skip.
    echo ===================================================
    set /p choice="Choose (1 or 2): "
    
    if "%choice%"=="1" (
        git pull origin main --rebase
        git push -u origin main
    ) else if "%choice%"=="2" (
        git push -u origin main --force
    )
)

echo.
echo ===================================================
echo Operation completed!
echo ===================================================
pause