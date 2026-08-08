@echo off
echo Cleaning up old scheduled tasks...
schtasks /delete /tn "FTS_Report_Morning" /f >nul 2>&1
schtasks /delete /tn "FTS_Report_Evening" /f >nul 2>&1
schtasks /delete /tn "FTS_Report_Night" /f >nul 2>&1
schtasks /delete /tn "FTS_Daily_Report" /f >nul 2>&1
echo.
echo All old scheduled tasks have been removed.
echo You can now use the new Dashboard.
pause
