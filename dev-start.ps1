$ErrorActionPreference = "Stop"

$projectRoot = "C:\Users\Owner\nova"
$backupScript = "C:\Users\Owner\nova\backup.ps1"
$preflightScript = "C:\Users\Owner\nova\preflight.ps1"

Write-Host ""
Write-Host "===============================" -ForegroundColor Cyan
Write-Host "Nova One-Click Dev Start" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path -LiteralPath $projectRoot)) {
    Write-Host "[ERROR] Project root missing -> $projectRoot" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $backupScript)) {
    Write-Host "[ERROR] backup.ps1 missing -> $backupScript" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $preflightScript)) {
    Write-Host "[ERROR] preflight.ps1 missing -> $preflightScript" -ForegroundColor Red
    exit 1
}

Set-Location $projectRoot

Write-Host "[1/3] Running backup..." -ForegroundColor Yellow
powershell -ExecutionPolicy Bypass -File $backupScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] backup.ps1 failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/3] Running preflight..." -ForegroundColor Yellow
powershell -ExecutionPolicy Bypass -File $preflightScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] preflight.ps1 failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3/3] Starting Nova..." -ForegroundColor Yellow
Write-Host ""

python -m uvicorn backend.main:app --reload