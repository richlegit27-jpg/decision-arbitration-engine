<#
.SYNOPSIS
  Run Nova Phase 4 with automatic checkpoint
.DESCRIPTION
  1. Creates a Phase 4 checkpoint of Nova folder before starting backend
  2. Starts Nova backend (uvicorn / Flask) automatically
  3. Safe to experiment — can rollback with phase4_checkpoint.ps1
#>

$NovaPath = "C:\Users\Owner\nova"
$BackupScript = Join-Path $NovaPath "phase4_checkpoint.ps1"

# Step 1: Create auto checkpoint
Write-Host "📦 Auto-checkpointing Nova Phase 4..."
& $BackupScript -Checkpoint

# Step 2: Stop any running Python processes
Write-Host "⛔ Stopping existing Python processes..."
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Step 3: Launch backend
Write-Host "🚀 Starting Nova backend on port 8743..."
py -m uvicorn app:app --reload --port 8743