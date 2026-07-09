$ErrorActionPreference = "Stop"

$root = "C:\Users\Owner\nova"
$publicCheck = Join-Path $root "tools\nova_public_release_check.ps1"
$adminCheck = Join-Path $root "tools\nova_admin_release_check.ps1"

Write-Host ""
Write-Host "NOVA FULL RELEASE CHECK"
Write-Host "Root: $root"
Write-Host ""

if (-not (Test-Path $publicCheck)) {
    throw "Missing public release check: $publicCheck"
}

if (-not (Test-Path $adminCheck)) {
    throw "Missing admin release check: $adminCheck"
}

Set-Location $root

Write-Host ""
Write-Host "Running public release check..."
Write-Host ""

powershell -ExecutionPolicy Bypass -File $publicCheck

Write-Host ""
Write-Host "Running admin release check..."
Write-Host ""

powershell -ExecutionPolicy Bypass -File $adminCheck

Write-Host ""
Write-Host "Checking working tree summary..."
git status --short

Write-Host ""
Write-Host "NOVA FULL RELEASE CHECK PASSED"
