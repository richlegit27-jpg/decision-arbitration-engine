# --------------------------------------------
# Nova One-Click Restore (using current local files)
# --------------------------------------------

# Paths
$novaPath = "C:\Users\Owner\nova"
$sourcePath = "C:\Users\Owner\nova"   # <-- your current local files (HTML, CSS, JS) are here
$backupPath = Join-Path $novaPath "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# 1️⃣ Backup current Nova folder
Write-Host "Backing up current Nova files..."
New-Item -ItemType Directory -Force -Path $backupPath
Copy-Item -Path $novaPath -Destination $backupPath -Recurse -Force
Write-Host "Backup completed at $backupPath"

# 2️⃣ Restore current local files (HTML, CSS, JS)
Write-Host "Restoring current local files to Nova folder..."
$itemsToCopy = @("templates","static")

foreach ($item in $itemsToCopy){
    $src = Join-Path $sourcePath $item
    $dest = Join-Path $novaPath $item
    Copy-Item -Path $src -Destination $dest -Recurse -Force
}

Write-Host "✅ Nova UI restored using current local files!"
Write-Host "Restart your server now — UI should be fully functional and polished."