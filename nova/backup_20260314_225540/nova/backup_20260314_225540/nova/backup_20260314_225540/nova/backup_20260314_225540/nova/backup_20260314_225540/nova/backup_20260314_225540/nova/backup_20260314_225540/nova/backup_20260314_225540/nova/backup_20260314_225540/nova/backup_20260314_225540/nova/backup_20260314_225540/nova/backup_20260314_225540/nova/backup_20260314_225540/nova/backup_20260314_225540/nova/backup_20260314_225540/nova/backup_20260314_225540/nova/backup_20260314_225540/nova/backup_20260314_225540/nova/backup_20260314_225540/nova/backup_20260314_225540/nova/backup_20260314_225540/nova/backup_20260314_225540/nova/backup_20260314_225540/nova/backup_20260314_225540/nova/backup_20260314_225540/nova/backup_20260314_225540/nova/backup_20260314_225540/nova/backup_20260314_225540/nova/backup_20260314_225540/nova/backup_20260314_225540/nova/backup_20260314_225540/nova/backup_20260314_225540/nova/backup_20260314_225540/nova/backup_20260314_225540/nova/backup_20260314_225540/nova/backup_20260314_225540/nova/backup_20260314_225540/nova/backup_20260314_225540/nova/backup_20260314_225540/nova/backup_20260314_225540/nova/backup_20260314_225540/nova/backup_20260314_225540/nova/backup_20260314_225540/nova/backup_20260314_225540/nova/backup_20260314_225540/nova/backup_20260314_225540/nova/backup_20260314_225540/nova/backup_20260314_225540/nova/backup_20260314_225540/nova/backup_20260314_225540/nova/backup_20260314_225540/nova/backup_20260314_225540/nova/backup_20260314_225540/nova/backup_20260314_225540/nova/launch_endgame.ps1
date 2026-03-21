# -----------------------------
# Nova Endgame Launch Script
# -----------------------------

# Paths
$backupZip = "C:\Users\Owner\nova_endgame_backup.zip"
$novaFolder = "C:\Users\Owner\nova"

# Step 1: Remove old folder (optional)
if(Test-Path $novaFolder){
    Write-Host "Removing existing Nova folder..."
    Remove-Item $novaFolder -Recurse -Force
}

# Step 2: Extract backup zip
Write-Host "Extracting Nova endgame backup..."
Add-Type -AssemblyName 'System.IO.Compression.FileSystem'
[System.IO.Compression.ZipFile]::ExtractToDirectory($backupZip, "C:\Users\Owner\")

# Step 3: Kill any existing backend process
$port=8792
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if($existing){ $existing | ForEach-Object { Stop-Process -Id $_ -Force } }

Start-Sleep -Milliseconds 300

# Step 4: Start FastAPI backend
Write-Host "Starting Nova backend on port $port..."
cd $novaFolder
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m uvicorn nova_ui_web:app --host 127.0.0.1 --port $port"

Start-Sleep -Seconds 2

# Step 5: Open browser automatically
Write-Host "Opening Nova app in default browser..."
Start-Process "http://127.0.0.1:$port/app?fresh=1"

Write-Host "✅ Nova Endgame Launched!"