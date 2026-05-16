<#
.SYNOPSIS
  Phase 4 One-Command Nova Launch
.DESCRIPTION
  1️⃣ Auto-checkpoint current Nova folder
  2️⃣ Stop existing Python backend
  3️⃣ Launch backend
  4️⃣ Open browser automatically
#>

$NovaPath = "C:\Users\Owner\nova"
$BackupScript = Join-Path $NovaPath "phase4_checkpoint.ps1"
$NovaUrl = "http://127.0.0.1:8743"

# 1. Auto-checkpoint
Write-Host "📦 Auto-checkpointing Nova..."
& $BackupScript -Checkpoint

# 2. Stop existing Python processes
Write-Host "⛔ Stopping any running Python backend..."
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 3. Launch backend asynchronously
Write-Host "🚀 Launching Nova backend..."
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$NovaPath'; py -m uvicorn app:app --reload --port 8743"

# 4. Open browser
Start-Sleep -Seconds 3
Write-Host "🌐 Opening Nova in default browser..."
Start-Process $NovaUrl

Write-Host "✅ Nova Phase 4 launched and ready!"