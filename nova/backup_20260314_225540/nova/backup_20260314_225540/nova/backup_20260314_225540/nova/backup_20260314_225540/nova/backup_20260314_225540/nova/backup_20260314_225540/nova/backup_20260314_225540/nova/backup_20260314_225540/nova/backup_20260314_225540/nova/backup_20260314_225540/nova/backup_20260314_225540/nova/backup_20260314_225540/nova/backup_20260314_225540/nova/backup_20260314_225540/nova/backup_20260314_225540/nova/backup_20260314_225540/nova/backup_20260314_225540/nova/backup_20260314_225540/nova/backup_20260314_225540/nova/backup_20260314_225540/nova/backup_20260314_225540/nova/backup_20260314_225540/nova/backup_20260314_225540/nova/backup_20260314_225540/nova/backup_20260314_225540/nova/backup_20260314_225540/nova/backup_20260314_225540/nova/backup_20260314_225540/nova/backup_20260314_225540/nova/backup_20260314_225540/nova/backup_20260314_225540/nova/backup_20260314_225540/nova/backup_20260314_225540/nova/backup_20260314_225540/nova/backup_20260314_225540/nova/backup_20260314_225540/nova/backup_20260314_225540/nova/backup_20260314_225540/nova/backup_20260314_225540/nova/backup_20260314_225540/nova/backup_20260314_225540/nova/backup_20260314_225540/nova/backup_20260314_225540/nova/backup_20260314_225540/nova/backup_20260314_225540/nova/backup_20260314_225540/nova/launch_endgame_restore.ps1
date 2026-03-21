# --------------------------------------------
# Nova Endgame UI Restore Script
# Restores templates + CSS + JS to original endgame versions
# --------------------------------------------

# Paths
$novaPath = "C:\Users\Owner\nova"
$templatesPath = Join-Path $novaPath "templates"
$staticPath = Join-Path $novaPath "static"

$backupPath = Join-Path $novaPath "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# 1️⃣ Backup current files
Write-Host "Backing up current templates and static files..."
New-Item -ItemType Directory -Force -Path $backupPath
Copy-Item -Path $templatesPath -Destination (Join-Path $backupPath "templates") -Recurse -Force
Copy-Item -Path $staticPath -Destination (Join-Path $backupPath "static") -Recurse -Force
Write-Host "Backup completed at $backupPath"

# 2️⃣ Restore original endgame templates
Write-Host "Restoring index.html template..."
$sourceIndex = "C:\Nova-Endgame\templates\index.html"   # <-- replace with your saved endgame version
Copy-Item -Path $sourceIndex -Destination (Join-Path $templatesPath "index.html") -Force

# 3️⃣ Restore original CSS files
Write-Host "Restoring CSS files..."
$cssFiles = @("base.css","layout.css")
foreach ($css in $cssFiles) {
    $sourceCss = "C:\Nova-Endgame\static\css\$css"  # <-- replace with your saved endgame version
    $destCss = Join-Path $staticPath ("css\" + $css)
    Copy-Item -Path $sourceCss -Destination $destCss -Force
}

# 4️⃣ Restore original JS files
Write-Host "Restoring JS files..."
$jsFiles = @("app.js","composer.js","memory-panel.js")
foreach ($js in $jsFiles) {
    $sourceJs = "C:\Nova-Endgame\static\js\$js"   # <-- replace with your saved endgame version
    $destJs = Join-Path $staticPath ("js\" + $js)
    Copy-Item -Path $sourceJs -Destination $destJs -Force
}

# 5️⃣ Final message
Write-Host "Nova endgame UI restore complete!"
Write-Host "✅ Templates, CSS, and JS restored to original endgame versions."
Write-Host "Backup of current broken files saved at: $backupPath"
Write-Host "You can now restart your server and the UI should be fully functional and polished."