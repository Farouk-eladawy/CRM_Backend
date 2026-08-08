@echo off
TITLE Stop OpenClaw Intelligent System
color 0C

echo ===================================================
echo       STOPPING OPENCLAW INTELLIGENT SYSTEM
echo ===================================================
echo.

echo Searching for running OpenClaw python processes...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'OpenClaw_Version\\(ai_agent|OpenClaw_Core|OpenClaw_Observer|dashboard)\\.py' }; " ^
  "if (-not $procs) { Write-Host 'No OpenClaw processes found.'; exit 0 }; " ^
  "Write-Host ('Found ' + $procs.Count + ' process(es):'); " ^
  "$procs | ForEach-Object { Write-Host ('- PID ' + $_.ProcessId + ' : ' + $_.CommandLine) }; " ^
  "$procs | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop; Write-Host ('Stopped PID ' + $_.ProcessId) } catch { Write-Host ('Failed to stop PID ' + $_.ProcessId + ' : ' + $_.Exception.Message) } }"

echo.
echo Done.
pause

