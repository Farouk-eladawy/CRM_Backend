@echo off
cd /d "c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject"
echo ==================================================
echo Starting Report Generation: %date% %time%
echo ==================================================

:: Run python and redirect output to both screen and file
python daily_report.py > last_run_log.txt 2>&1

:: Display the log content
type last_run_log.txt

echo.
echo ==================================================
echo Execution Finished. Check last_run_log.txt for details.
echo ==================================================

:: Pause to keep window open during manual test
pause
