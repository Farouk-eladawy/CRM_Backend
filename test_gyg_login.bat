@echo off
chcp 65001 > nul
title Test GYG Login
cd /d "%~dp0"
echo Testing GYG auto-login...
echo Close ALL other GYG tabs in Edge and Cursor before continuing.
echo.
python test_gyg_login.py
pause
