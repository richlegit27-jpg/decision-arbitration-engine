$ErrorActionPreference = "Stop"

$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$projectRoot = "C:\Users\Owner\nova"
$backupRoot = "C:\Users\Owner\nova_backups"
$backupPath = Join-Path $backupRoot "nova_$stamp"

New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
Copy-Item -Path "$projectRoot\*" -Destination $backupPath -Recurse -Force

Write-Host ""
Write-Host "Backup complete:" -ForegroundColor Green
Write-Host $backupPath -ForegroundColor Cyan
Write-Host ""

Get-ChildItem $backupPath | Select-Object Name, LastWriteTime