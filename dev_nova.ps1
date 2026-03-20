$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\Owner\nova"
$SaveScript = "C:\Users\Owner\nova\save_nova.ps1"
$PreflightScript = "C:\Users\Owner\nova\preflight_nova.ps1"
$StartScript = "C:\Users\Owner\nova\start_nova.ps1"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
}

function Assert-PathExists {
    param(
        [string]$Path,
        [string]$Label
    )

    if (-not (Test-Path $Path)) {
        Write-Host "$Label not found: $Path" -ForegroundColor Red
        exit 1
    }
}

Assert-PathExists -Path $ProjectRoot -Label "Project root"
Assert-PathExists -Path $SaveScript -Label "Save script"
Assert-PathExists -Path $PreflightScript -Label "Preflight script"
Assert-PathExists -Path $StartScript -Label "Start script"

Write-Step "STEP 1 - SAVE NOVA"
& $SaveScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "Save step failed." -ForegroundColor Red
    exit 1
}

Write-Step "STEP 2 - PREFLIGHT CHECK"
& $PreflightScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "Preflight failed. Nova will not start." -ForegroundColor Red
    exit 1
}

Write-Step "STEP 3 - START NOVA"
& $StartScript
exit $LASTEXITCODE