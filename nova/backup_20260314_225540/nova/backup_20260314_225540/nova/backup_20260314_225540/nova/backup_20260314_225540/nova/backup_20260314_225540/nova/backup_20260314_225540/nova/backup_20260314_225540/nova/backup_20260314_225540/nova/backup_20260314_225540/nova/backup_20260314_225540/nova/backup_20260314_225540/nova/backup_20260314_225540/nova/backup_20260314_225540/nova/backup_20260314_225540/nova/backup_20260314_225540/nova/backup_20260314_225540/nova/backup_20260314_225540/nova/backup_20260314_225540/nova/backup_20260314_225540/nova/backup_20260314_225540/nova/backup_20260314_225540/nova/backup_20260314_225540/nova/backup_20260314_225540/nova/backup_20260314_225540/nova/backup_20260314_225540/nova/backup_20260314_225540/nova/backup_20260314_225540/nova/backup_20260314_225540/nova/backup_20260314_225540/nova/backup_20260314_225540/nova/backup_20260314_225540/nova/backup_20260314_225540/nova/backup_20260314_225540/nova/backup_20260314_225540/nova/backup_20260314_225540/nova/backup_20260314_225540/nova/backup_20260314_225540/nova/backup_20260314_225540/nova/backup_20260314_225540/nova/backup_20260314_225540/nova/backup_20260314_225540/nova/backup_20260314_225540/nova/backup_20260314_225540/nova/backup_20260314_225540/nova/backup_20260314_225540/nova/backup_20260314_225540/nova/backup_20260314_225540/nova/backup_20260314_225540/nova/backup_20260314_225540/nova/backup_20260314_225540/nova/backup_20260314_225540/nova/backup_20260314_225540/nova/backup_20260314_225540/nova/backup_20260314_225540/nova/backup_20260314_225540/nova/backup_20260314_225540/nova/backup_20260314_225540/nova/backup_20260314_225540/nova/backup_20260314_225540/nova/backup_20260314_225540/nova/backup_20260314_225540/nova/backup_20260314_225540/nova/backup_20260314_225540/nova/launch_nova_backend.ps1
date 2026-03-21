# -----------------------------
# Nova Endgame One-Click Backend Launcher
# -----------------------------

$port = 8000
$backendFolder = "C:\Users\Owner\nova\backend"
$backendFile = "main.py"
$novaUrl = "http://127.0.0.1:8000"

# Kill any existing backend processes on port 8000
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if($existing){ $existing | ForEach-Object { Stop-Process -Id $_ -Force } }

Start-Sleep -Milliseconds 300

# Navigate to backend folder
Set-Location $backendFolder

# Start the FastAPI backend using python -m uvicorn
Start-Process "python" -ArgumentList "-m uvicorn $backendFile:app --reload --port $port" -NoNewWindow

# Wait a few seconds for the server to start
Start-Sleep -Seconds 3

# Open browser to Nova frontend
Start-Process $novaUrl

Write-Host "✅ Nova backend started and browser opened at $novaUrl"