@echo off
echo.
echo ========================================================
echo  YOUR TASKS ONLY - Test Railway BEFORE stopping local
echo ========================================================
echo.
echo A) In Railway Dashboard
echo    1. Open project: dazzling-amazement
echo    2. Confirm service is Running / Healthy
echo    3. Confirm Persistent Volume mounted at: /app/data
echo    4. Variables must include at least:
echo         FTS_DATA_DIR=/app/data
echo         AIRTABLE_API_KEY / AIRTABLE_BASE_ID
echo         OPENAI_API_KEY / DEEPSEEK_API_KEY
echo         WHATSAPP_* / FACEBOOK_*
echo       Do NOT hardcode PORT (Railway sets it)
echo    5. Copy your public Railway URL, example:
echo         https://YOUR-SERVICE.up.railway.app
echo.
echo B) Test API without touching live webhooks
echo    1. Open in browser:
echo         https://YOUR-SERVICE.up.railway.app/api/chats?limit=5
echo       Expect JSON (or auth/error JSON), NOT Railway crash page
echo    2. If it fails, open Railway Logs and send me the error
echo.
echo C) Temporary frontend test (local CRM stays live)
echo    1. Keep production dashboard on current API
echo    2. On ONE test browser/profile only, set:
echo         VITE_API_BASE=https://YOUR-SERVICE.up.railway.app/api
echo       OR open a temporary build pointing to Railway
echo    3. Check:
echo         - Login works
echo         - Inbox shows chats
echo         - Open one Religious chat
echo         - Customer note / Ad Name column visible
echo         - Customers Contact table loads
echo.
echo D) DO NOT do these yet
echo    - Do NOT stop local Windows CRM
echo    - Do NOT switch WhatsApp/Facebook webhooks
echo    - Do NOT point all agents to Railway
echo.
echo E) When all tests above PASS, tell me:
echo    "Railway staging OK"
echo    Then we run FINAL cutover together:
echo      stop local -^> migrate_db_to_railway.bat -^> switch webhooks
echo.
echo ========================================================
echo.
