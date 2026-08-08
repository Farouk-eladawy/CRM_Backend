$lockFile = "C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\.git\index.lock"
Write-Host "Looking for process locking: $lockFile"

# Method 1: Check all processes' open handles using CIM
$processes = Get-CimInstance -ClassName Win32_Process | Where-Object { $_.Name -match '\.exe$' }
Write-Host ("Total processes: " + $processes.Count)

# Method 2: Use sysinternal's handle.exe if available  
$handlePath = Get-Command handle.exe -ErrorAction SilentlyContinue
if ($handlePath) {
    Write-Host "Found handle.exe at: $($handlePath.Source)"
    & handle.exe -accepteula -nobanner "$lockFile"
} else {
    Write-Host "handle.exe not found. Checking if sysinternals is available..."
    # Try common locations
    $paths = @(".\handle64.exe", ".\handle.exe", "C:\tools\handle.exe", "C:\Sysinternals\handle.exe")
    foreach ($p in $paths) {
        if (Test-Path $p) {
            Write-Host "Found at: $p"
            & $p -accepteula -nobanner "$lockFile"
            break
        }
    }
}

# Method 3: Check openfiles
Write-Host "`nChecking openfiles..."
$result = openfiles /query /v 2>$null
if ($LASTEXITCODE -eq 0) {
    $result | Select-String -Pattern "index.lock" | ForEach-Object { Write-Host $_ }
} else {
    Write-Host "openfiles requires elevated privileges (Run as Admin)"
}

Write-Host "`nDone."
