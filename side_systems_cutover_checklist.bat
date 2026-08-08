@echo off
echo.
echo ========================================================
echo  Side systems checklist - change API URL on cutover day
echo ========================================================
echo.
echo A) MUST change URL when api.ftstravels.com points to Railway
echo --------------------------------------------------------
echo 1. Send Report For Guide
echo    File: Send Report For Guide\.env
echo    Change:
echo      DASHBOARD_API_BASE_URL=http://localhost:5001
echo    To:
echo      DASHBOARD_API_BASE_URL=https://api.ftstravels.com
echo    Then restart schedule / Run_Continuous if running.
echo.
echo 2. Netlify Frontend Dashboard
echo    Env: VITE_API_BASE
echo    Should be:
echo      https://api.ftstravels.com/api
echo    (If already using api.ftstravels.com, no code change needed
echo     after DNS flip. If any build still points to localhost, rebuild.)
echo.
echo B) Stay on Windows PC - NOT moved by Railway
echo --------------------------------------------------------
echo 1. Send Report For Guide itself (PowerShell + Task Scheduler)
echo 2. Airtable_Phone_Correction (talks to Airtable only)
echo 3. Bukon_Server (Bokun -^> Airtable only)
echo 4. Evolution WhatsApp on :8080 (needs tunnel/host plan)
echo 5. OpenClaw Core on :18789 (optional/learning)
echo.
echo C) Inside CRM automations (127.0.0.1:5001)
echo --------------------------------------------------------
echo Pickup / Invoice / Photographer / Review / Collect /
echo Religious follow-ups / booking_communications
echo -^> These call the SAME server from inside.
echo -^> On Railway they keep working as internal loopback.
echo -^> No side .env change needed.
echo.
echo D) Ignore (dev/test only)
echo --------------------------------------------------------
echo test_*.py / check_*.py that hardcode localhost:5001
echo.
echo ========================================================
echo Cutover order tip:
echo  1) Railway healthy + DB uploaded
echo  2) Flip DNS for api.ftstravels.com
echo  3) Update Send Report For Guide .env
echo  4) Verify one manual Run_Send_Report.bat -DryRun then real
echo  5) Only then stop local CRM
echo ========================================================
echo.
pause
