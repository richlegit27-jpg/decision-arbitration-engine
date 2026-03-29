# Phase 4 Launch Script
# Backup current Nova, restore Phase 4 bundle, and launch Flask

$novaDir = "C:\Users\Owner\nova"
$backupDir = "$novaDir\phase4_backup_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
$bundlePath = "C:\Users\Owner\Desktop\nova_phase4_endgame.zip"

Write-Host "Backing up current Nova to $backupDir"
robocopy $novaDir $backupDir /E

Write-Host "Extracting Phase 4 bundle from $bundlePath..."
Expand-Archive $bundlePath -DestinationPath $novaDir -Force

Write-Host "Launching Nova Phase 4..."
cd $novaDir
python app.py