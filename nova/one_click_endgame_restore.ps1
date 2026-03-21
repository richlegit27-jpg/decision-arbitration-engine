# --------------------------------------------
# Nova One-Click Endgame Restore
# --------------------------------------------

$novaPath   = "C:\Users\Owner\nova"                   # Active Nova project folder
$sourcePath = "C:\Users\Owner\nova_endgame_source"   # Clean final copy folder
$backupPath = Join-Path $novaPath "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

Write-Host "Backing up current Nova folder..."
New-Item -ItemType Directory -Force -Path $backupPath
Copy-Item -Path $novaPath -Destination $backupPath -Recurse -Force
Write-Host "Backup completed at $backupPath"

Write-Host "Cleaning up old backup files in final copy..."
# Templates cleanup
$templatesPath = Join-Path $sourcePath "templates"
Get-ChildItem -Path $templatesPath -Include "*.bak_*","*.BACKUP_*","*.WORKING_*" -File -Recurse | Remove-Item -Force

# Static JS cleanup
$jsPath = Join-Path $sourcePath "static\js"
Get-ChildItem -Path $jsPath -Include "*.bak_*","*.BAK_*","*.WORKING_*" -File -Recurse | Remove-Item -Force

# Static CSS cleanup (optional)
$cssPath = Join-Path $sourcePath "static\css"
Get-ChildItem -Path $cssPath -Include "*.bak_*","*.BAK_*","*.WORKING_*" -File -Recurse | Remove-Item -Force

Write-Host "Restoring final copy into active Nova folder..."
$itemsToCopy = @("templates","static")
foreach ($item in $itemsToCopy){
    $src  = Join-Path $sourcePath $item
    $dest = Join-Path $novaPath $item
    Copy-Item -Path $src -Destination $dest -Recurse -Force
}

Write-Host "✅ Nova UI fully restored and cleaned!"
Write-Host "Restart your Nova server now — everything should work perfectly."