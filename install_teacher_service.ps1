[CmdletBinding()]
param(
    [string]$ServiceName = "",
    [string]$NssmPath = "",
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Resolve-ProjectRoot {
    param([string]$ScriptPath)
    if ($ProjectRoot) {
        return (Resolve-Path $ProjectRoot).Path
    }
    return (Split-Path -Parent $ScriptPath)
}

function Load-ConfigValues {
    param([string]$RootPath)
    $configPath = Join-Path $RootPath "config.json"
    if (-not (Test-Path $configPath)) {
        return $null
    }
    try {
        return Get-Content $configPath -Raw | ConvertFrom-Json
    } catch {
        Write-Warning "Could not parse config.json. Script will use fallback defaults."
        return $null
    }
}

if (-not (Test-IsAdmin)) {
    throw "Please run PowerShell as Administrator, then run this script again."
}

$scriptPath = $MyInvocation.MyCommand.Path
$resolvedRoot = Resolve-ProjectRoot -ScriptPath $scriptPath
$config = Load-ConfigValues -RootPath $resolvedRoot

if (-not $ServiceName) {
    $ServiceName = [string]($config.system.teacher_service_name)
}
if (-not $ServiceName) {
    $ServiceName = "FTS Teacher"
}

if (-not $NssmPath) {
    $NssmPath = [string]($config.system.nssm_path)
}
if (-not $NssmPath) {
    $NssmPath = "C:\Tools\nssm\win64\nssm.exe"
}

$NssmPath = [Environment]::ExpandEnvironmentVariables($NssmPath)
$runnerBat = Join-Path $resolvedRoot "run_teacher_service.bat"
$logsDir = Join-Path $resolvedRoot "logs"
$stdoutLog = Join-Path $logsDir "teacher-service-stdout.log"
$stderrLog = Join-Path $logsDir "teacher-service-stderr.log"
$cmdPath = Join-Path $env:WINDIR "System32\cmd.exe"
$appParameters = "/c `"$runnerBat`""

if (-not (Test-Path $NssmPath)) {
    throw "nssm.exe not found at: $NssmPath"
}
if (-not (Test-Path $runnerBat)) {
    throw "run_teacher_service.bat not found at: $runnerBat"
}
if (-not (Test-Path $cmdPath)) {
    throw "cmd.exe not found at: $cmdPath"
}

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$serviceExists = $null
try {
    $serviceExists = Get-Service -Name $ServiceName -ErrorAction Stop
} catch {
    $serviceExists = $null
}

if ($serviceExists) {
    Write-Host "Updating existing service: $ServiceName"
    & $NssmPath set $ServiceName Application $cmdPath
    & $NssmPath set $ServiceName AppParameters $appParameters
} else {
    Write-Host "Installing new service: $ServiceName"
    & $NssmPath install $ServiceName $cmdPath $appParameters
}

& $NssmPath set $ServiceName AppDirectory $resolvedRoot
& $NssmPath set $ServiceName AppStdout $stdoutLog
& $NssmPath set $ServiceName AppStderr $stderrLog
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateBytes 1048576
& $NssmPath set $ServiceName Start SERVICE_AUTO_START
& $NssmPath set $ServiceName AppExit Default Restart
& $NssmPath set $ServiceName Description "FTS Teacher backend service for dashboard APIs, WhatsApp webhook, email processing, and workflows."

Write-Host "Ensuring service startup type is automatic..."
sc.exe config $ServiceName start= auto | Out-Null

Write-Host "Restarting service..."
& $NssmPath restart $ServiceName | Out-Null

Write-Host ""
Write-Host "Service setup completed successfully."
Write-Host "Service Name : $ServiceName"
Write-Host "NSSM Path    : $NssmPath"
Write-Host "Project Root : $resolvedRoot"
Write-Host "Runner BAT   : $runnerBat"
Write-Host "Stdout Log   : $stdoutLog"
Write-Host "Stderr Log   : $stderrLog"
Write-Host ""
Write-Host "Health check URL:"
Write-Host "http://127.0.0.1:5001/api/system/status"
