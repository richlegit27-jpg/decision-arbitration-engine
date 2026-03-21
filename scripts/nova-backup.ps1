param(
    [string]$ProjectRoot = "C:\Users\Owner\nova",
    [string]$BackupRoot = "C:\Users\Owner\nova_backups",
    [switch]$Zip
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[INFO] $msg" -ForegroundColor Cyan
}

function Write-Good($msg) {
    Write-Host "[OK]   $msg" -ForegroundColor Green
}

function Write-WarnMsg($msg) {
    Write-Host "[WARN] $msg" -ForegroundColor Yellow
}

if (-not (Test-Path $ProjectRoot)) {
    throw "Project root not found: $ProjectRoot"
}

if (-not (Test-Path $BackupRoot)) {
    New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "nova_backup_$stamp"
$backupPath = Join-Path $BackupRoot $backupName

Write-Info "Creating backup folder..."
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null

Write-Info "Copying project..."
Copy-Item -Path $ProjectRoot -Destination $backupPath -Recurse -Force

$copiedProjectPath = Join-Path $backupPath (Split-Path $ProjectRoot -Leaf)
Write-Good "Project copied to: $copiedProjectPath"

if ($Zip) {
    $zipPath = Join-Path $BackupRoot "$backupName.zip"
    Write-Info "Creating zip archive..."
    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }
    Compress-Archive -Path $copiedProjectPath -DestinationPath $zipPath -Force
    Write-Good "Zip created: $zipPath"
}

Write-Good "Backup complete."