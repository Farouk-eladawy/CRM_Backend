@echo off
cd /d "%~dp0"
if exist "..\.venv\Scripts\activate.bat" (
  call "..\.venv\Scripts\activate.bat"
) else (
  if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
  )
)
if exist ".dbg\server-auto-stop.env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".dbg\server-auto-stop.env") do set "%%A=%%B"
)
if not exist ".dbg" mkdir ".dbg"
set "RESTART_LOG=.dbg\teacher_service_restart.log"
set "RESTART_DELAY=5"

:run_loop
echo [%date% %time%] Starting ai_agent.py>>"%RESTART_LOG%"
python ai_agent.py
set "EXIT_CODE=%ERRORLEVEL%"
echo [%date% %time%] ai_agent.py exited with code %EXIT_CODE%>>"%RESTART_LOG%"

if "%EXIT_CODE%"=="0" (
  echo ai_agent.py exited normally with code 0.
  goto :eof
)

if "%EXIT_CODE%"=="-1073741510" (
  echo ai_agent.py was interrupted by user. Not restarting.
  goto :eof
)

echo ai_agent.py crashed or stopped unexpectedly with code %EXIT_CODE%. Restarting in %RESTART_DELAY% seconds...
timeout /t %RESTART_DELAY% /nobreak >nul
goto run_loop
