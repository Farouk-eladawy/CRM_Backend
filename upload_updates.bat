@echo off
echo ===================================================
echo   Pushing updates to FTS_AI_CRM_Demo GitHub Repo
echo ===================================================

git init
git add .gitignore
git add frontend_dashboard/
git add ai_agent.py
git add *.py
git add *.md

git commit -m "UI/UX Redesign Implementation & Enhancements"
git branch -M main

git remote add origin https://github.com/Farouk-eladawy/-FTS_AI_CRM_Demo.git 2>nul
git remote set-url origin https://github.com/Farouk-eladawy/-FTS_AI_CRM_Demo.git

echo Pushing to GitHub...
git push -u origin main -f

echo.
echo ===================================================
echo   Push Complete!
echo ===================================================
pause
