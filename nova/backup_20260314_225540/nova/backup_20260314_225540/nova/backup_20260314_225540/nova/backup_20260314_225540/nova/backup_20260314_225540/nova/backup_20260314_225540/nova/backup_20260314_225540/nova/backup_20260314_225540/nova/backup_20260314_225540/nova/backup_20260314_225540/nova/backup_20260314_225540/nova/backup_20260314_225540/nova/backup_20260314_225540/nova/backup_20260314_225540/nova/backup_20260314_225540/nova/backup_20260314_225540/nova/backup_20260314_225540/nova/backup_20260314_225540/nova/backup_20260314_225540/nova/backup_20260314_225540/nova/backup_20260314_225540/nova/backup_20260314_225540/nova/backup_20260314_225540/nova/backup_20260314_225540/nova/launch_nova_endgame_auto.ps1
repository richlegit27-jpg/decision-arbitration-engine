# -----------------------------
# Nova Endgame One-Click Auto-Update Launcher
# -----------------------------

# Paths
$novaExe = "C:\Users\Owner\nova\dist\NovaEndgame.exe"
$backupZip = "C:\Users\Owner\nova\backup\NovaEndgame.zip"
$novaUrl = "http://127.0.0.1:8792/app?fresh=1"

# Kill any previous Nova backend
$port = 8792
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if($existing){ $existing | ForEach-Object { Stop-Process -Id $_ -Force } }

Start-Sleep -Milliseconds 300

# Check for backup zip and update .exe if needed
if(Test-Path $backupZip){
    $zipTime = (Get-Item $backupZip).LastWriteTime
    $exeTime = if(Test-Path $novaExe){ (Get-Item $novaExe).LastWriteTime } else { Get-Date "1/1/2000" }

    if($zipTime -gt $exeTime){
        Write-Host "🔄 Updating NovaEndgame.exe from backup..."
        # Remove old exe
        if(Test-Path $novaExe){ Remove-Item $novaExe -Force }

        # Extract from zip
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($backupZip, "C:\Users\Owner\nova\dist")
        Write-Host "✅ Update complete!"
    }
}

# Launch the standalone Nova executable
Start-Process -FilePath $novaExe

# Give it a moment to start
Start-Sleep -Seconds 3

# Open the default browser to Nova workspace
Start-Process $novaUrl

Write-Host "🚀 Nova Endgame Launched!"