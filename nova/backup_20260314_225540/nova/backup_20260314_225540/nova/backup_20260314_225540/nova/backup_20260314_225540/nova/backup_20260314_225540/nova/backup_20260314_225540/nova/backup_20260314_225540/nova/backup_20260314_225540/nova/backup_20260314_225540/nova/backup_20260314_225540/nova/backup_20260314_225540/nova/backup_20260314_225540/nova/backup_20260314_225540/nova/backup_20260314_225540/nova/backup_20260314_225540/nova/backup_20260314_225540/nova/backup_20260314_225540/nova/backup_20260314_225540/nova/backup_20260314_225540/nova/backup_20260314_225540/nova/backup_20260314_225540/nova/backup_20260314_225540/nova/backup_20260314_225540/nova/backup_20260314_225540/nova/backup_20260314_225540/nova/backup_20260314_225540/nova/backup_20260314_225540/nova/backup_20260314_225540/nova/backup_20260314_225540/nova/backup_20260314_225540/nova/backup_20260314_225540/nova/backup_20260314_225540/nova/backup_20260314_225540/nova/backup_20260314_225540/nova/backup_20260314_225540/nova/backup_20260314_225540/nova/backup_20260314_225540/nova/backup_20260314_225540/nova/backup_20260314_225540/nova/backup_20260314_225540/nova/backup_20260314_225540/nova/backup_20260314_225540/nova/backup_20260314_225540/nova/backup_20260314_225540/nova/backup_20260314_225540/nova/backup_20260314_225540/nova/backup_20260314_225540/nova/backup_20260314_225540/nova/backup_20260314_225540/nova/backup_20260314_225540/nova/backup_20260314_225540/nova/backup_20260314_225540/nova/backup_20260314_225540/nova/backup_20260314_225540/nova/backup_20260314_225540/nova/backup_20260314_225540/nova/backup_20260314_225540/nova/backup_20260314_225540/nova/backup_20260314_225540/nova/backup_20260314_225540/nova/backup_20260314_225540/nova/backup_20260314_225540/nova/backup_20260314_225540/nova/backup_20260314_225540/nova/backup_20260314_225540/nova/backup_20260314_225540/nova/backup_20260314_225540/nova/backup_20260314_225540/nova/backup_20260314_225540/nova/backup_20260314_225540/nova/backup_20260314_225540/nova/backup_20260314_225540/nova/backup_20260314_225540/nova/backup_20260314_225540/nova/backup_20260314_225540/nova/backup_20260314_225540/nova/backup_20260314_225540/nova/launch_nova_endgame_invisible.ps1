# -----------------------------
# Nova Endgame Invisible One-Click Launcher
# -----------------------------

# -----------------------------
# Config
# -----------------------------
$novaExe       = "C:\Users\Owner\nova\dist\NovaEndgame.exe"
$localBackup   = "C:\Users\Owner\nova\backup\NovaEndgame.zip"
$networkBackup = "\\Shared\NovaBuilds\NovaEndgame.zip"  # Optional
$novaUrl       = "http://127.0.0.1:8792/app?fresh=1"
$port          = 8792
$logFile       = "C:\Users\Owner\nova\launcher_log.txt"

# Function to write log
function Log($msg){
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $msg" | Out-File -FilePath $logFile -Append -Encoding UTF8
}

# -----------------------------
# Kill existing Nova backend
# -----------------------------
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if($existing){ $existing | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
Start-Sleep -Milliseconds 300

# -----------------------------
# Determine newest backup
# -----------------------------
$backups = @()
if(Test-Path $localBackup){ $backups += $localBackup }
if(Test-Path $networkBackup){ $backups += $networkBackup }

$updated = $false
if($backups.Count -gt 0){
    $newestBackup = $backups | Sort-Object { (Get-Item $_).LastWriteTime } -Descending | Select-Object -First 1
    $zipTime      = (Get-Item $newestBackup).LastWriteTime
    $exeTime      = if(Test-Path $novaExe){ (Get-Item $novaExe).LastWriteTime } else { Get-Date "1/1/2000" }

    if($zipTime -gt $exeTime){
        if(Test-Path $novaExe){ Remove-Item $novaExe -Force -ErrorAction SilentlyContinue }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($newestBackup, "C:\Users\Owner\nova\dist")
        Get-ChildItem "C:\Users\Owner\nova\dist\*.tmp" -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        $updated = $true
        Log "Updated NovaEndgame.exe from $newestBackup"
    }
}

# -----------------------------
# Launch Nova silently
# -----------------------------
Start-Process -FilePath $novaExe -WindowStyle Hidden
Start-Sleep -Seconds 3

# -----------------------------
# Open workspace silently
# -----------------------------
Start-Process $novaUrl
if($updated){ Log "Opened workspace with latest version" } else { Log "Opened workspace with existing version" }

# -----------------------------
# Done
# -----------------------------
Exit