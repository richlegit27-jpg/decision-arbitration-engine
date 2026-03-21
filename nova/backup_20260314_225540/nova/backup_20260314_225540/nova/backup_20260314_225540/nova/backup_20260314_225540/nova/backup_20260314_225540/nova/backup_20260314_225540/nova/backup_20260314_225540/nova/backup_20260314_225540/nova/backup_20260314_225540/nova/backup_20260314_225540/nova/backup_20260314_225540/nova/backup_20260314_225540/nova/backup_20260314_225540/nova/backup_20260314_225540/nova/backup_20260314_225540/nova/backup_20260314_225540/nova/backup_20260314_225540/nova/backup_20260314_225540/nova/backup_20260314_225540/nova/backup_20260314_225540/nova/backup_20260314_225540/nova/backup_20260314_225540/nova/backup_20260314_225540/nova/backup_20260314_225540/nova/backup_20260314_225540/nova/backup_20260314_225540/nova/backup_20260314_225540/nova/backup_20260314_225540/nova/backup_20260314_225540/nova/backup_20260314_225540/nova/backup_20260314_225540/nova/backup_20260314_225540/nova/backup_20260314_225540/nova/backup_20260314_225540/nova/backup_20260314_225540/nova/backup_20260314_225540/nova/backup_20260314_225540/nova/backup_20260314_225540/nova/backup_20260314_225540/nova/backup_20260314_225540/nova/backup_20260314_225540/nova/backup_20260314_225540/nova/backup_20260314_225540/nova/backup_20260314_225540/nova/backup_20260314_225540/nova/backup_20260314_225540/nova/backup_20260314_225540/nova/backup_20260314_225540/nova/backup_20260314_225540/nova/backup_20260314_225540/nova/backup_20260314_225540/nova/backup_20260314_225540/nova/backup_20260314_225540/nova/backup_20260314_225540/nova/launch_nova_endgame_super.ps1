# -----------------------------
# Nova Super Endgame 3.0 One-Click Launcher
# -----------------------------
$novaExe       = "C:\Users\Owner\nova\dist\NovaEndgame.exe"
$localBackup   = "C:\Users\Owner\nova\backup\NovaEndgame.zip"
$networkBackup = "\\Shared\NovaBuilds\NovaEndgame.zip"
$onlineUrl     = "https://yourserver.com/builds/NovaEndgame.zip"
$novaUrl       = "http://127.0.0.1:8792/app?fresh=1"
$port          = 8792
$logFile       = "C:\Users\Owner\nova\launcher_log.txt"
$tempDownload  = "$env:TEMP\NovaEndgame_online.zip"

function Log($msg){
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $msg" | Out-File -FilePath $logFile -Append -Encoding UTF8
}

# Kill existing Nova backend
$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if($existing){ $existing | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
Start-Sleep -Milliseconds 300

# Determine newest build
$updated = $false
$newestBackup = $null

# Online build
try {
    $req = Invoke-WebRequest -Uri $onlineUrl -Method Head -UseBasicParsing -ErrorAction Stop
    $onlineTime = Get-Date $req.Headers.'Last-Modified'
    $exeTime    = if(Test-Path $novaExe){ (Get-Item $novaExe).LastWriteTime } else { Get-Date "1/1/2000" }
    if($onlineTime -gt $exeTime){
        Invoke-WebRequest -Uri $onlineUrl -OutFile $tempDownload -UseBasicParsing -ErrorAction Stop
        $newestBackup = $tempDownload
        Log "Downloaded online build."
    }
} catch {
    Log "Online build unavailable, using fallback."
}

# Network/local backup
$backups = @()
if(Test-Path $localBackup){ $backups += $localBackup }
if(Test-Path $networkBackup){ $backups += $networkBackup }

if($backups.Count -gt 0){
    $backupNewest = $backups | Sort-Object { (Get-Item $_).LastWriteTime } -Descending | Select-Object -First 1
    $exeTime      = if(Test-Path $novaExe){ (Get-Item $novaExe).LastWriteTime } else { Get-Date "1/1/2000" }
    $backupTime   = (Get-Item $backupNewest).LastWriteTime
    if(-not $newestBackup -or $backupTime -gt (Get-Item $newestBackup).LastWriteTime){
        $newestBackup = $backupNewest
    }
}

# Apply update
if($newestBackup){
    if(Test-Path $novaExe){ Remove-Item $novaExe -Force -ErrorAction SilentlyContinue }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($newestBackup, "C:\Users\Owner\nova\dist")
    Get-ChildItem "C:\Users\Owner\nova\dist\*.tmp" -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    $updated = $true
    Log "Updated NovaEndgame.exe from $newestBackup"
    if(Test-Path $tempDownload){ Remove-Item $tempDownload -Force -ErrorAction SilentlyContinue }
}

# Launch Nova
Start-Process -FilePath $novaExe -WindowStyle Hidden
Start-Sleep -Seconds 3

# Open workspace
Start-Process $novaUrl
if($updated){ Log "Opened workspace with latest build" } else { Log "Opened workspace with existing build" }

Exit