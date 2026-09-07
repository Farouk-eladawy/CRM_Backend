# Download GitHub CLI without winget. Installs to tools\gh\gh.exe
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DestDir = Join-Path $Root "tools\gh"
$GhExe = Join-Path $DestDir "gh.exe"

if (Test-Path -LiteralPath $GhExe) {
    Write-Host "[OK] GitHub CLI already exists: $GhExe"
    & $GhExe --version
    exit 0
}

Write-Host "[INFO] Downloading latest GitHub CLI for Windows..."
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/cli/cli/releases/latest" -Headers @{ "User-Agent" = "fts-crm-backup" }
$asset = $release.assets | Where-Object { $_.name -match 'windows_amd64\.zip$' } | Select-Object -First 1
if (-not $asset) {
    Write-Host "[ERROR] Could not find windows_amd64.zip in the latest gh release."
    exit 1
}

$tmpZip = Join-Path $env:TEMP "gh-windows-amd64.zip"
$tmpDir = Join-Path $env:TEMP "gh-windows-extract"
if (Test-Path -LiteralPath $tmpZip) { Remove-Item -LiteralPath $tmpZip -Force }
if (Test-Path -LiteralPath $tmpDir) { Remove-Item -LiteralPath $tmpDir -Recurse -Force }

Write-Host ("[INFO] " + $asset.browser_download_url)
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $tmpZip -UseBasicParsing
Expand-Archive -LiteralPath $tmpZip -DestinationPath $tmpDir -Force

$found = Get-ChildItem -LiteralPath $tmpDir -Recurse -Filter "gh.exe" | Select-Object -First 1
if (-not $found) {
    Write-Host "[ERROR] gh.exe was not inside the downloaded zip."
    exit 1
}

New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
Copy-Item -LiteralPath $found.FullName -Destination $GhExe -Force
Remove-Item -LiteralPath $tmpZip -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $tmpDir -Recurse -Force -ErrorAction SilentlyContinue

if (-not (Test-Path -LiteralPath $GhExe)) {
    Write-Host "[ERROR] Copy failed."
    exit 1
}

Write-Host "[OK] Installed GitHub CLI to $GhExe"
& $GhExe --version
exit 0
