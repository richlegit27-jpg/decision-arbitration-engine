# -----------------------------
# Nova Endgame One-Click Launcher
# -----------------------------

$port = 8000
$novaBackend = "C:\Users\Owner\nova\backend\main.py"
$novaUrl = "http://127.0.0.1:8000"

# Kill any existing backend running on the port
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if($existing){ $existing | ForEach-Object { Stop-Process -Id $_ -Force } }

Start-Sleep -Milliseconds 300

# Launch FastAPI backend
Start-Process "python" -ArgumentList "`"$novaBackend`"" -NoNewWindow

# Give backend time to start
Start-Sleep -Seconds 3

# Open browser
Start-Process $novaUrl

Write-Host "✅ Nova Endgame Launched at $novaUrl"