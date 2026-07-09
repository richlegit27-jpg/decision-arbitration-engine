$ErrorActionPreference = "Stop"

$root = "C:\Users\Owner\nova"
$localCheck = Join-Path $root "tools\nova_full_release_check.ps1"
$railwayCheck = Join-Path $root "tools\nova_railway_release_check.ps1"

function Invoke-NovaCheckedScript {
    param(
        [string]$Label,
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        throw "Missing $Label script: $Path"
    }

    Write-Host ""
    Write-Host $Label
    Write-Host ""

    & powershell -ExecutionPolicy Bypass -File $Path
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        throw "$Label failed with exit code $exitCode"
    }
}

Write-Host ""
Write-Host "NOVA SHIP CHECK"
Write-Host "Root: $root"
Write-Host ""

Set-Location $root

Invoke-NovaCheckedScript -Label "Step 1/2: Local full release check" -Path $localCheck
Invoke-NovaCheckedScript -Label "Step 2/2: Railway live release check" -Path $railwayCheck

Write-Host ""
Write-Host "Final git status:"
git status --short

Write-Host ""
Write-Host "NOVA SHIP CHECK PASSED"
