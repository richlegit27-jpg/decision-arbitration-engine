$ErrorActionPreference = "Continue"

$projectRoot = "C:\Users\Owner\nova"
$backendDir = "C:\Users\Owner\nova\backend"
$dataDir = "C:\Users\Owner\nova\backend\data"
$templatesDir = "C:\Users\Owner\nova\templates"
$staticDir = "C:\Users\Owner\nova\static"
$jsDir = "C:\Users\Owner\nova\static\js"
$cssDir = "C:\Users\Owner\nova\static\css"

Write-Host ""
Write-Host "===============================" -ForegroundColor Cyan
Write-Host "Nova Doctor" -ForegroundColor Cyan
Write-Host "Self-Healing Repair Tool" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

function Fix-Folder {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Host "[FIX] Creating folder -> $Path" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
    else {
        Write-Host "[OK] Folder exists -> $Path" -ForegroundColor Green
    }
}

function Fix-Package {
    param([string]$Package)

    $check = python -m pip show $Package 2>$null

    if (-not $check) {
        Write-Host "[FIX] Installing $Package..." -ForegroundColor Yellow
        python -m pip install $Package
    }
    else {
        Write-Host "[OK] $Package installed" -ForegroundColor Green
    }
}

Write-Host "Checking project folders..."
Fix-Folder $projectRoot
Fix-Folder $backendDir
Fix-Folder $dataDir
Fix-Folder $templatesDir
Fix-Folder $staticDir
Fix-Folder $jsDir
Fix-Folder $cssDir

Write-Host ""
Write-Host "Checking Python packages..."

Fix-Package "fastapi"
Fix-Package "uvicorn"
Fix-Package "openai"
Fix-Package "jinja2"

Write-Host ""
Write-Host "Checking state file..."

$stateFile = "$dataDir\nova_state.json"

if (-not (Test-Path $stateFile)) {

    Write-Host "[FIX] Creating default state file..." -ForegroundColor Yellow

    $defaultState = @"
{
  "active_model": "gpt-4.1-mini",
  "users": {}
}
"@

    $defaultState | Out-File $stateFile -Encoding UTF8
}
else {
    Write-Host "[OK] State file exists"
}

Write-Host ""
Write-Host "Testing backend import..."

Push-Location $projectRoot

try {
    python -c "import backend.main"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] backend.main imports correctly" -ForegroundColor Green
    }
    else {
        Write-Host "[WARNING] backend.main import failed" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "[ERROR] backend.main crashed during import" -ForegroundColor Red
}

Pop-Location

Write-Host ""
Write-Host "==============================="
Write-Host "Nova Doctor Complete"
Write-Host "==============================="
Write-Host ""

Write-Host "Recommended next step:"
Write-Host ""
Write-Host "powershell -ExecutionPolicy Bypass -File C:\Users\Owner\nova\dev-start.ps1"
Write-Host ""