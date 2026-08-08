@echo off
TITLE Upload Frontend - FTS AI CRM
color 0A

:: ============================================================
::  UPLOAD FRONTEND DASHBOARD TO GITHUB
::  - يرفع التعديلات على الـ Frontend (submodule) ثم
::  - يحدث الـ main repo عشان يشير للـ commit الجديد
:: ============================================================

setlocal enabledelayedexpansion

:: --- المسارات ---
set "SCRIPT_DIR=%~dp0"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend_dashboard"
set "NSSM_PATH=%SCRIPT_DIR%NSSM_v2.25\win64\nssm.exe"
set "SERVICE_NAME=FTS Teacher"

echo ╔══════════════════════════════════════════════════╗
echo ║        رفع تحديثات الواجهة الأمامية              ║
echo ║     Upload Frontend Dashboard to GitHub          ║
echo ╚══════════════════════════════════════════════════╝
echo.

:: ─── 1. الذهاب إلى مجلد الفرونت إند ───
echo [1/6] 📂 الذهاب إلى مجلد Frontend...
cd /d "%FRONTEND_DIR%"
if errorlevel 1 (
    echo ❌ خطأ: لم يتم العثور على المجلد: %FRONTEND_DIR%
    pause
    exit /b 1
)
echo    ✅ المسار: %CD%
echo.

:: ─── 2. إيقاف الخدمة مؤقتاً (لفتح الملفات المقفولة) ───
echo [2/6] ⏸️  إيقاف خدمة FTS Teacher مؤقتاً...
if exist "%NSSM_PATH%" (
    "%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>&1
    if errorlevel 1 (
        echo    ⚠️  لم يستطع إيقاف الخدمة (قد تحتاج صلاحيات Admin)
        echo    ℹ️  المتابعة عادي، لكن ممكن يكون في ملفات مقفولة
    ) else (
        echo    ✅ تم إيقاف الخدمة بنجاح
        timeout /t 2 /nobreak >nul
    )
) else (
    echo    ⚠️  NSSM غير موجود - نتخطى خطوة إيقاف الخدمة
)
echo.

:: ─── 3. عرض الملفات المعدلة ───
echo [3/6] 📋 الملفات المعدلة (Git Status):
echo    ───────────────────────────────────────────
git status --short
echo    ───────────────────────────────────────────
echo.

:: ─── 4. إضافة وتثبيت التغييرات ───
echo [4/6] 💾 إضافة وحفظ التغييرات...
git add .

:: طلب رسالة Commit
echo.
set /p commit_msg="✏️  أدخل رسالة التحديث (أو Enter للافتراضي): "
if "%commit_msg%"=="" set commit_msg=Update frontend dashboard - %date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%

:: إزالة المسافات من الوقت
set commit_msg=%commit_msg: =_%

git commit -m "%commit_msg%"
if errorlevel 1 (
    echo    ℹ️  لا توجد تغييرات جديدة أو فشل الـ commit
    echo    هل تتابع رفع أي تغييرات سابقة؟ (Y/N)
    set /p continue_choice=": "
    if /i "!continue_choice!" neq "Y" (
        echo.
        echo ⚠️  تم إلغاء الرفع.
        pause
        exit /b 0
    )
)
echo    ✅ تم الحفظ
echo.

:: ─── 5. رفع التغييرات إلى GitHub ───
echo [5/6] 📤 رفع التغييرات إلى GitHub (submodule)...

:: التأكد من وجود remote
git remote remove origin 2>nul
git remote add origin https://github.com/Farouk-eladawy/fts-chat-dashboard.git

:: محاولة الرفع أولاً بدون force
echo.
echo    جاري الرفع...
git push -u origin main
if errorlevel 1 (
    echo.
    echo ╔═════════════════════════════════════════════╗
    echo ║  ⚠️  فشل الرفع - يوجد تعارض مع الـ Remote  ║
    echo ╠═════════════════════════════════════════════╣
    echo ║  1️⃣  سحب التغييرات أولاً ثم رفع (Pull+Push) ║
    echo ║  2️⃣  رفع قسري (Force Push) - يتجاهل الـ Remote ║
    echo ║  3️⃣  إلغاء                                   ║
    echo ╚═════════════════════════════════════════════╝
    echo.
    set /p push_choice="🔀 اختر (1 أو 2 أو 3): "
    
    if "!push_choice!"=="1" (
        echo.
        echo    جاري سحب التغييرات من الـ Remote...
        git pull origin main --rebase
        if errorlevel 1 (
            echo    ❌ فشل السحب. جرب Force Push بدلاً من ذلك.
            set /p force_confirm="⚠️  Force Push? (Y/N): "
            if /i "!force_confirm!"=="Y" (
                git push -u origin main --force
            ) else (
                echo    ❌ تم الإلغاء.
            )
        ) else (
            echo    ✅ تم السحب. جاري الرفع...
            git push -u origin main
        )
    ) else if "!push_choice!"=="2" (
        echo.
        echo ⚠️  أنت على وشك Force Push - هذا سيحذف أي تغييرات في الـ Remote
        set /p force_confirm="⚠️  هل أنت متأكد? (N/Y): "
        if /i "!force_confirm!"=="Y" (
            git push -u origin main --force
            if !errorlevel! equ 0 (
                echo    ✅ تم الرفع القسري بنجاح
            ) else (
                echo    ❌ فشل الرفع القسري. جرب مرة أخرى أو استخدم GitHub Desktop.
            )
        ) else (
            echo    ❌ تم الإلغاء.
        )
    ) else (
        echo    ❌ تم إلغاء الرفع.
    )
) else (
    echo    ✅ تم رفع الـ submodule بنجاح!
)
echo.

:: ─── 6. العودة للمستودع الرئيسي وتحديث الـ Submodule Pointer ───
echo [6/6] 🔄 تحديث الـ main repository مع submodule pointer...
cd /d "%SCRIPT_DIR%"

:: تحديث مؤشر الـ submodule
git add frontend_dashboard
git commit -m "Update frontend submodule pointer - %date:~-4,4%%date:~-10,2%%date:~-7,2%"

echo.
echo    هل تريد رفع التحديث إلى الـ Main Repository أيضاً؟ (Y/N)
set /p main_push=": "
if /i "!main_push!"=="Y" (
    echo.
    echo    جاري رفع الـ main repository...
    git push origin main
    if errorlevel 1 (
        echo    ⚠️  فشل الرفع. حاول Force Push؟
        set /p force_main="Force Push? (Y/N): "
        if /i "!force_main!"=="Y" (
            git push origin main --force
            if !errorlevel! equ 0 (
                echo    ✅ تم رفع الـ main repo بنجاح
            ) else (
                echo    ❌ فشل - قد يكون الـ repo كبير جداً (حاول من GitHub Desktop)
            )
        )
    ) else (
        echo    ✅ تم رفع الـ main repository بنجاح!
    )
) else (
    echo    ℹ️  تخطينا رفع الـ main repository.
)
echo.

:: ─── 7. إعادة تشغيل الخدمة ───
echo ⏯️  إعادة تشغيل خدمة FTS Teacher...
if exist "%NSSM_PATH%" (
    "%NSSM_PATH%" start "%SERVICE_NAME%" >nul 2>&1
    if errorlevel 1 (
        echo    ⚠️  لم يستطع إعادة تشغيل الخدمة (شغلها يدوياً: nssm start "FTS Teacher")
    ) else (
        echo    ✅ تم إعادة تشغيل الخدمة بنجاح
    )
)
echo.

echo ╔══════════════════════════════════════════════════╗
echo ║        ✅  تم الانتهاء بنجاح!                    ║
echo ║     Frontend uploaded to GitHub                  ║
echo ╚══════════════════════════════════════════════════╝
echo.

pause
