$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = "C:\Users\Owner\nova"
$SurfaceSmoke = Join-Path $Root "tools\nova_public_surface_lock_smoke.py"

Write-Host ""
Write-Host "NOVA PUBLIC RELEASE CHECK"
Write-Host "Root: $Root"
Write-Host ""

if (-not (Test-Path $SurfaceSmoke)) {
    throw "Missing public surface smoke: $SurfaceSmoke"
}

Write-Host "Running locked public surface smoke."
Write-Host ""

& python $SurfaceSmoke

if ($LASTEXITCODE -ne 0) {
    throw "Public surface smoke failed."
}

Write-Host ""
Write-Host "Checking working tree for accidental mobile changes."
Write-Host ""

$statusLines = @(
    git -C $Root status --short
)

$mobileChanges = @(
    $statusLines |
        Where-Object {
            $_ -match "static[\\/]js[\\/]mobile[\\/]" -or
            $_ -match "static[\\/]css[\\/]nova-mobile\.css" -or
            $_ -match "templates[\\/]mobile\.html" -or
            $_ -match "templates[\\/]index-mobile\.html"
        }
)

Write-Host "Current git status:"

foreach ($line in $statusLines) {
    Write-Host $line
}

if ($mobileChanges.Count -gt 0) {
    Write-Host ""
    Write-Host "ACCIDENTAL MOBILE CHANGES DETECTED:"

    foreach ($line in $mobileChanges) {
        Write-Host $line
    }

    throw "Public release check blocked by mobile file changes."
}

Write-Host ""
Write-Host "NOVA PUBLIC RELEASE CHECK PASSED"
