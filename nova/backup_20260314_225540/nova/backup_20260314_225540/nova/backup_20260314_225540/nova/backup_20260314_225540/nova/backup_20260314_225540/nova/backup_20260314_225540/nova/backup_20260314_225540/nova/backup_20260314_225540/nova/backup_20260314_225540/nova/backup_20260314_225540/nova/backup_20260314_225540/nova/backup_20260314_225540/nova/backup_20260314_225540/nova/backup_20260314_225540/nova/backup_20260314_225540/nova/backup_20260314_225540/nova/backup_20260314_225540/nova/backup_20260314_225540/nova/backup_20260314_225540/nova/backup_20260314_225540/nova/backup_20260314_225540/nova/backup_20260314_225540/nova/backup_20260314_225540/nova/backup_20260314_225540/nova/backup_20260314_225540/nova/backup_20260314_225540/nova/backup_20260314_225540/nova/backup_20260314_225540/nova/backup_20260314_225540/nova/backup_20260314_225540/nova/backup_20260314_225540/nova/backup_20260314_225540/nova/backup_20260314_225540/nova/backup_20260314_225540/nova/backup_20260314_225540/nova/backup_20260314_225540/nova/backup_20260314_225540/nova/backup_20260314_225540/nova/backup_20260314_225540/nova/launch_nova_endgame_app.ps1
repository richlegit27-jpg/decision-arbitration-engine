# -----------------------------
# Nova Endgame One-Click Launcher
# -----------------------------

# Path to your standalone NovaEndgame.exe
$novaExe = "C:\Users\Owner\nova\dist\NovaEndgame.exe"
$novaUrl = "http://127.0.0.1:8792/app?fresh=1"

# Kill any previous Nova backend
$port = 8792
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if($existing){ $existing | ForEach-Object { Stop-Process -Id $_ -Force } }

Start-Sleep -Milliseconds 300

# Launch the standalone Nova executable
Start-Process -FilePath $novaExe

# Give it a moment to start
Start-Sleep -Seconds 3

# Open the default browser to Nova workspace
Start-Process $novaUrl

Write-Host "✅ Nova Endgame Launched!"