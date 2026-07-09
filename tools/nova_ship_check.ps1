$ErrorActionPreference = "Stop"

$root = "C:\Users\Owner\nova"
$localCheck = Join-Path $root "tools\nova_full_release_check.ps1"
$railwayCheck = Join-Path $root "tools\nova_railway_release_check.ps1"

Write-Host ""
Write-Host "NOVA SHIP CHECK"
Write-Host "Root: $root"
Write-Host ""

if (-not (Test-Path $localCheck)) {
    throw "Missing local full release check: $localCheck"
}

if (-not (Test-Path $railwayCheck)) {
    throw "Missing Railway release check: $railwayCheck"
}

Set-Location $root

Write-Host ""
Write-Host "Step 1/2: Local full release check"
Write-Host ""

powershell -ExecutionPolicy Bypass -File $localCheck

Write-Host ""
Write-Host "Step 2/2: Railway live release check"
Write-Host ""

powershell -ExecutionPolicy Bypass -File $railwayCheck

Write-Host ""
Write-Host "Final git status:"
git status --short

Write-Host ""
Write-Host "NOVA SHIP CHECK PASSED"
