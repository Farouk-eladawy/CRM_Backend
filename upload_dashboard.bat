@echo off
TITLE Push Dashboard to GitHub
color 0A

:: الانتقال إلى مجلد لوحة التحكم
cd /d "%~dp0frontend_dashboard"

echo ===================================================
echo       UPLOADING DASHBOARD TO GITHUB
echo ===================================================
echo Working Directory: %CD%

:: التحقق مما إذا كان مجلد git موجوداً، إذا لم يكن كذلك نقوم بإنشائه
if not exist ".git" (
    echo [1/5] Initializing Git repository...
    git init
    git branch -M main
    git remote add origin https://github.com/Farouk-eladawy/AI_Agent_CRM.git
) else (
    echo [1/5] Git repository already initialized.
)

:: إضافة جميع الملفات الجديدة والمعدلة
echo [2/5] Adding files...
git add .

:: إنشاء رسالة التزام (Commit) بالتاريخ والوقت
echo [3/5] Committing changes...
set mydate=%date:~-4,4%%date:~-10,2%%date:~-7,2%
set mytime=%time:~0,2%%time:~3,2%
set mytime=%mytime: =0%
git commit -m "Update Dashboard - %mydate%_%mytime%"

:: رفع الملفات إلى GitHub
echo [4/5] Pushing to GitHub (main branch)...
git push -u origin main

echo.
echo ===================================================
echo [5/5] SUCCESS! Files uploaded to GitHub.
echo ===================================================
echo You can now go to Netlify and deploy or refresh your site.
echo.
pause