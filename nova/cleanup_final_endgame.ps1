# --------------------------------------------
# Nova Endgame Final Copy Cleanup
# --------------------------------------------

$sourcePath = "C:\Users\Owner\nova_endgame_source"

Write-Host "Cleaning up old backup files in $sourcePath ..."

# -----------------------------
# Templates folder cleanup
# -----------------------------
$templatesPath = Join-Path $sourcePath "templates"

# Delete old .bak, .BACKUP, .WORKING files
Get-ChildItem -Path $templatesPath -Include "*.bak_*","*.BACKUP_*","*.WORKING_*" -File -Recurse | Remove-Item -Force

# -----------------------------
# Static JS folder cleanup
# -----------------------------
$jsPath = Join-Path $sourcePath "static\js"

# Delete old .bak, .BAK, .WORKING JS files
Get-ChildItem -Path $jsPath -Include "*.bak_*","*.BAK_*","*.WORKING_*" -File -Recurse | Remove-Item -Force

# -----------------------------
# Optional: static/css cleanup (if any old backups exist)
# -----------------------------
$cssPath = Join-Path $sourcePath "static\css"
Get-ChildItem -Path $cssPath -Include "*.bak_*","*.BAK_*","*.WORKING_*" -File -Recurse | Remove-Item -Force

Write-Host "✅ Cleanup complete. Only latest working files remain."