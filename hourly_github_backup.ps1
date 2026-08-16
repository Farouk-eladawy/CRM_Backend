# Hourly private-repo backup.
# main branch: project files + small secrets (no force-push).
# crm-data branch / GitHub Release: latest database zip only.
$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

$LogFile = Join-Path $Root "hourly_github_backup.log"
$LockFile = Join-Path $Root ".hourly_github_backup.lock"
$ZipPath = Join-Path $Root "hourly_data_backup\fts_crm_data_latest.zip"
$Stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$GitHubFileLimit = 95MB
$Origin = "https://github.com/Farouk-eladawy/CRM_Backend.git"

$ForceCommit = @(
    "config.json",
    "railway_vars.json",
    "token.json",
    "token_sales.json",
    "credentials.json",
    "credentials_sales.json",
    "google_reviews_token.json"
)

function Write-BackupLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs)
    $output = & git @GitArgs 2>&1
    $code = $LASTEXITCODE
    return @{ Code = $code; Output = ($output | Out-String).Trim() }
}

if (Test-Path -LiteralPath $LockFile) {
    $lockAgeHours = ((Get-Date) - (Get-Item -LiteralPath $LockFile).LastWriteTime).TotalHours
    if ($lockAgeHours -lt 2) {
        Write-BackupLog "SKIP: another backup is still running."
        exit 0
    }
    Write-BackupLog "WARN: stale lock file found, continuing."
    Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
}

Set-Content -LiteralPath $LockFile -Value $PID -Encoding ASCII

try {
    if (-not (Test-Command "git")) {
        Write-BackupLog "ERROR: git is not installed or not in PATH."
        exit 1
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Root ".git"))) {
        Write-BackupLog "ERROR: this folder is not a git repo. Refusing to git init."
        exit 1
    }

    $remote = Invoke-Git remote get-url origin
    if ($remote.Code -eq 0) {
        Invoke-Git remote set-url origin $Origin | Out-Null
    } else {
        Invoke-Git remote add origin $Origin | Out-Null
    }

    Write-BackupLog "START backup to $Origin"

    if (Test-Command "python") {
        & python "build_hourly_data_bundle.py"
        if ($LASTEXITCODE -ne 0) {
            Write-BackupLog "WARN: data zip build failed; code/secrets backup will still continue."
        } else {
            Write-BackupLog "OK: data zip built"
        }
    } else {
        Write-BackupLog "WARN: python not in PATH, skipped data zip."
    }

    Invoke-Git add -A | Out-Null
    foreach ($item in $ForceCommit) {
        $full = Join-Path $Root $item
        if (Test-Path -LiteralPath $full) {
            Invoke-Git add -f -- $item | Out-Null
        }
    }
    Get-ChildItem -LiteralPath $Root -File -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -like "client_secret_*.json" -or
        $_.Name -like "token*.json" -or
        $_.Name -like "credentials*.json"
    } | ForEach-Object {
        Invoke-Git add -f -- $_.Name | Out-Null
    }

    $staged = Invoke-Git diff --cached --name-only
    if ($staged.Code -eq 0 -and $staged.Output) {
        foreach ($path in ($staged.Output -split "\r?\n")) {
            $name = $path.Trim()
            if ($name -like "*.db" -or $name -like "*.db-wal" -or $name -like "*.db-shm") {
                Invoke-Git restore --staged -- $name | Out-Null
            }
        }
    }

    $pending = Invoke-Git diff --cached --quiet
    if ($pending.Code -eq 0) {
        Write-BackupLog "OK: no staged project/secret changes on main."
    } else {
        $message = "Hourly backup $Stamp"
        $commit = Invoke-Git commit -m $message
        if ($commit.Code -ne 0) {
            Write-BackupLog ("ERROR: git commit failed. " + $commit.Output)
            exit 1
        }
        $push = Invoke-Git push origin HEAD:main
        if ($push.Code -ne 0) {
            Write-BackupLog ("ERROR: git push to main failed. Local commit is kept; no force push was used. " + $push.Output)
            exit 1
        }
        Write-BackupLog "OK: pushed '$message' to main"
    }

    if (-not (Test-Path -LiteralPath $ZipPath)) {
        Write-BackupLog "WARN: data zip not found, skipped database upload."
        exit 0
    }

    $zipSize = (Get-Item -LiteralPath $ZipPath).Length
    Write-BackupLog ("INFO: data zip size {0:N1} MB" -f ($zipSize / 1MB))

    if (Test-Command "gh") {
        & gh release view crm-data-latest >$null 2>&1
        if ($LASTEXITCODE -ne 0) {
            & gh release create crm-data-latest $ZipPath --title "FTS CRM latest data" --notes "Rolling private snapshot. Replaced every hour. Contains DB + config + Gmail tokens."
        } else {
            & gh release upload crm-data-latest $ZipPath --clobber
        }
        if ($LASTEXITCODE -eq 0) {
            Write-BackupLog "OK: uploaded data zip to GitHub Release crm-data-latest"
            exit 0
        }
        Write-BackupLog "WARN: gh release upload failed, trying crm-data branch."
    }

    if ($zipSize -gt $GitHubFileLimit) {
        Write-BackupLog "ERROR: zip is over GitHub git file limit (100MB). Install GitHub CLI and run gh auth login so the zip can go to a Release instead of git history."
        exit 1
    }

    $tmp = Join-Path $env:TEMP "fts-crm-data-backup"
    if (Test-Path -LiteralPath $tmp) {
        Remove-Item -LiteralPath $tmp -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tmp | Out-Null
    Copy-Item -LiteralPath $ZipPath -Destination (Join-Path $tmp "fts_crm_data_latest.zip")

    Push-Location -LiteralPath $tmp
    try {
        & git init | Out-Null
        & git add fts_crm_data_latest.zip
        & git -c user.email="backup@local" -c user.name="Hourly Backup" commit -m "Latest data snapshot $Stamp"
        & git remote add origin $Origin
        & git branch -M crm-data
        & git push --force origin crm-data
        if ($LASTEXITCODE -ne 0) {
            Write-BackupLog "ERROR: force-push of crm-data branch failed."
            exit 1
        }
        Write-BackupLog "OK: replaced crm-data branch with latest zip only"
    }
    finally {
        Pop-Location
    }

    exit 0
}
catch {
    Write-BackupLog ("ERROR: " + $_.Exception.Message)
    exit 1
}
finally {
    Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
}
