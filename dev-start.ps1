$ErrorActionPreference = "Stop"

$projectRoot = "C:\Users\Owner\nova"

Write-Host ""
Write-Host "===============================" -ForegroundColor Cyan
Write-Host "Nova Dev Start" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path -LiteralPath $projectRoot)) {
    Write-Host "[ERROR] Project root missing -> $projectRoot" -ForegroundColor Red
    exit 1
}

Set-Location $projectRoot

$existing = Get-NetTCPConnection `
    -LocalPort 5001 `
    -State Listen `
    -ErrorAction SilentlyContinue

if ($existing) {
    Write-Host "[INFO] Port 5001 is already in use." -ForegroundColor Yellow

    foreach ($connection in $existing) {
        Write-Host "[INFO] Stopping process $($connection.OwningProcess)" -ForegroundColor Yellow

        Stop-Process `
            -Id $connection.OwningProcess `
            -Force `
            -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds 1
}

Write-Host "[STARTING] Nova application..." -ForegroundColor Green
Write-Host "[URL] http://127.0.0.1:5001" -ForegroundColor Cyan
Write-Host ""

python .\app.py