param(
    [string]$ProjectRoot = "C:\Users\Owner\nova"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[INFO] $msg" -ForegroundColor Cyan
}

function Write-Good($msg) {
    Write-Host "[OK]   $msg" -ForegroundColor Green
}

function Write-Bad($msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
}

$checksFailed = $false

$requiredPaths = @(
    "C:\Users\Owner\nova\backend\main.py",
    "C:\Users\Owner\nova\templates\index.html",
    "C:\Users\Owner\nova\static\js\app-fixed.js",
    "C:\Users\Owner\nova\static\js\composer.js",
    "C:\Users\Owner\nova\static\js\memory-panel.js",
    "C:\Users\Owner\nova\static\js\ui-hotfix.js",
    "C:\Users\Owner\nova\static\js\nova-toast.js",
    "C:\Users\Owner\nova\static\js\nova-modal.js"
)

Write-Info "Checking required files..."
foreach ($path in $requiredPaths) {
    if (Test-Path $path) {
        Write-Good $path
    }
    else {
        Write-Bad $path
        $checksFailed = $true
    }
}

Write-Info "Checking Python import syntax..."
try {
    Push-Location $ProjectRoot
    python -m py_compile "backend\main.py"
    Pop-Location
    Write-Good "backend\main.py compiles"
}
catch {
    if (Get-Location) {
        try { Pop-Location } catch {}
    }
    Write-Bad "backend\main.py failed compile"
    $checksFailed = $true
}

Write-Info "Checking backup folder..."
if (-not (Test-Path "C:\Users\Owner\nova_backups")) {
    New-Item -ItemType Directory -Path "C:\Users\Owner\nova_backups" -Force | Out-Null
    Write-Good "Created backup folder"
}
else {
    Write-Good "Backup folder exists"
}

if ($checksFailed) {
    Write-Host ""
    Write-Bad "Preflight failed."
    exit 1
}

Write-Host ""
Write-Good "Preflight passed."
exit 0