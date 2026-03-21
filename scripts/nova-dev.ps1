param(
    [string]$ProjectRoot = "C:\Users\Owner\nova",
    [string]$BackupRoot = "C:\Users\Owner\nova_backups"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[INFO] $msg" -ForegroundColor Cyan
}

Write-Info "Running backup..."
& "C:\Users\Owner\nova\scripts\nova-backup.ps1" -ProjectRoot $ProjectRoot -BackupRoot $BackupRoot

Write-Info "Running preflight..."
& "C:\Users\Owner\nova\scripts\nova-preflight.ps1" -ProjectRoot $ProjectRoot

Write-Info "Starting Nova dev server..."
Set-Location $ProjectRoot
python -m uvicorn backend.main:app --reload