$ErrorActionPreference = "Stop"

$projectRoot = "C:\Users\Owner\nova"

Write-Host ""
Write-Host "Nova preflight check" -ForegroundColor Cyan
Write-Host "Project: $projectRoot"
Write-Host ""

$requiredFiles = @(
    "backend\main.py",
    "backend\routers\chat_stream.py",
    "static\js\app-fixed.js",
    "static\js\app-render.js",
    "static\js\composer.js",
    "static\js\controls.js",
    "static\js\sidebar.js",
    "static\js\memory-panel.js",
    "static\js\voice.js",
    "templates\index.html",
    "backup.ps1"
)

Write-Host "Checking required files..." -ForegroundColor Yellow
foreach ($file in $requiredFiles) {
    $fullPath = Join-Path $projectRoot $file
    if (Test-Path $fullPath) {
        Write-Host "[OK] $file" -ForegroundColor Green
    }
    else {
        Write-Host "[MISSING] $file" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Checking duplicate script tags in templates\index.html..." -ForegroundColor Yellow

$indexPath = Join-Path $projectRoot "templates\index.html"
if (Test-Path $indexPath) {
    $content = Get-Content $indexPath -Raw

    $scriptTargets = @(
        "/static/js/app-fixed.js",
        "/static/js/app-render.js",
        "/static/js/composer.js",
        "/static/js/controls.js",
        "/static/js/sidebar.js",
        "/static/js/memory-panel.js",
        "/static/js/voice.js"
    )

    foreach ($target in $scriptTargets) {
        $count = ([regex]::Matches($content, [regex]::Escape($target))).Count
        if ($count -eq 1) {
            Write-Host "[OK] $target loaded once" -ForegroundColor Green
        }
        elseif ($count -eq 0) {
            Write-Host "[MISSING] $target not found" -ForegroundColor Red
        }
        else {
            Write-Host "[DUPLICATE] $target appears $count times" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "Checking latest backup..." -ForegroundColor Yellow

$backupRoot = "C:\Users\Owner\nova_backups"
if (Test-Path $backupRoot) {
    $latestBackup = Get-ChildItem $backupRoot -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestBackup) {
        Write-Host "[OK] Latest backup: $($latestBackup.FullName)" -ForegroundColor Green
    }
    else {
        Write-Host "[WARN] No backup folders found." -ForegroundColor Yellow
    }
}
else {
    Write-Host "[WARN] Backup root not found: $backupRoot" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Preflight complete." -ForegroundColor Cyan
Write-Host ""