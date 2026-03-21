param(
    [Parameter(Mandatory = $true)]
    [string]$BackupProjectPath,

    [string]$ProjectRoot = "C:\Users\Owner\nova"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[INFO] $msg" -ForegroundColor Cyan
}

function Write-Good($msg) {
    Write-Host "[OK]   $msg" -ForegroundColor Green
}

if (-not (Test-Path $BackupProjectPath)) {
    throw "Backup path not found: $BackupProjectPath"
}

$backupItem = Get-Item $BackupProjectPath
if (-not $backupItem.PSIsContainer) {
    throw "Backup path must be the backed-up nova folder, not a zip or single file: $BackupProjectPath"
}

$projectParent = Split-Path $ProjectRoot -Parent
if (-not (Test-Path $projectParent)) {
    New-Item -ItemType Directory -Path $projectParent -Force | Out-Null
}

$tempOld = "$ProjectRoot.before_restore_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss")

if (Test-Path $ProjectRoot) {
    Write-Info "Moving current project out of the way..."
    Move-Item -Path $ProjectRoot -Destination $tempOld -Force
    Write-Good "Current project moved to: $tempOld"
}

Write-Info "Restoring backup..."
Copy-Item -Path $BackupProjectPath -Destination $ProjectRoot -Recurse -Force

Write-Good "Restore complete: $ProjectRoot"
Write-Host ""
Write-Host "Previous project copy kept at:" -ForegroundColor Yellow
Write-Host $tempOld -ForegroundColor Yellow