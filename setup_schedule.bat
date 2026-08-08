@echo off
echo Setting up Automatic Shift Reports (Adjusted for UTC-8 System Time)...
cd /d "c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject"

:: Delete old tasks if exists
schtasks /delete /tn "FTS_Report_Morning" /f >nul 2>&1
schtasks /delete /tn "FTS_Report_Evening" /f >nul 2>&1
schtasks /delete /tn "FTS_Report_Night" /f >nul 2>&1

:: Create 3 Tasks for the 3 Shifts (Converted to UTC-8 System Time)

:: 1. Cairo 18:05 (Morning Shift End) -> System Time 08:05 AM
schtasks /create /tn "FTS_Report_Morning" /tr "\"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\run_report.bat\"" /sc DAILY /st 08:05

:: 2. Cairo 00:05 (Evening Shift End) -> System Time 14:05 (02:05 PM)
schtasks /create /tn "FTS_Report_Evening" /tr "\"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\run_report.bat\"" /sc DAILY /st 14:05

:: 3. Cairo 08:05 (Night Shift End) -> System Time 22:05 (10:05 PM)
schtasks /create /tn "FTS_Report_Night" /tr "\"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\run_report.bat\"" /sc DAILY /st 22:05

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS! Tasks scheduled based on your system time (UTC-8):
    echo 1. Morning Report: Runs at 08:05 AM local (equals 06:05 PM Cairo)
    echo 2. Evening Report: Runs at 02:05 PM local (equals 12:05 AM Cairo)
    echo 3. Night Report:   Runs at 10:05 PM local (equals 08:05 AM Cairo)
) else (
    echo.
    echo Warning: Some tasks might not have been created if not running as Administrator.
)
pause
