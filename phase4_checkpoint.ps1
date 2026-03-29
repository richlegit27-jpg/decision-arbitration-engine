<#
.SYNOPSIS
  Nova Phase 4 Auto-Checkpoint & Rollback
.DESCRIPTION
  One-command backup/restore system:
    - Creates timestamped checkpoint copies of your Nova folder
    - Can rollback to the last checkpoint instantly
.NOTES
  Usage:
    .\phase4_checkpoint.ps1 -Checkpoint        # create a new checkpoint
    .\phase4_checkpoint.ps1 -Rollback          # rollback to last checkpoint
#>

param(
    [switch]$Checkpoint,
    [switch]$Rollback
)

$NovaPath = "C:\Users\Owner\nova"
$BackupRoot = "C:\Users\Owner\nova_backups_phase4"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

# Ensure backup folder exists
if (-not (Test-Path $BackupRoot)) {
    New-Item -ItemType Directory -Path $BackupRoot | Out-Null
}

if ($Checkpoint) {
    $dest = Join-Path $BackupRoot "nova_checkpoint_$timestamp"
    Write-Host "📦 Creating Phase 4 checkpoint: $dest"
    # Mirror Nova folder to backup
    Robocopy $NovaPath $dest /MIR /Z /XA:H /XD "__pycache__" | Out-Null
    Write-Host "✅ Checkpoint created successfully."
}

elseif ($Rollback) {
    # Find most recent checkpoint
    $latest = Get-ChildItem $BackupRoot -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        Write-Host "⚠️ No checkpoints found in $BackupRoot"
        return
    }

    Write-Host "⏪ Rolling back to latest checkpoint: $($latest.FullName)"
    # Remove current Nova folder safely
    Remove-Item $NovaPath -Recurse -Force
    # Copy latest checkpoint back
    Robocopy $latest.FullName $NovaPath /MIR /Z /XA:H | Out-Null
    Write-Host "✅ Rollback complete. Nova restored to checkpoint."
}

else {
    Write-Host "Usage:"
    Write-Host "  -Checkpoint : Create a new Phase 4 checkpoint"
    Write-Host "  -Rollback   : Rollback Nova to latest checkpoint"
}