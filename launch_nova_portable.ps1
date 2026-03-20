# -----------------------------
# Nova Ultimate 2026 Launch Script
# -----------------------------

# Pick dynamic port
$backendPort = Get-Random -Minimum 8700 -Maximum 8800
Write-Host "Launching Nova Ultimate 2026..."
Write-Host "Backend port: $backendPort" -ForegroundColor Cyan

# Start backend
$backendProcess = Start-Process -FilePath "python.exe" -ArgumentList "nova_app.py" -WorkingDirectory $PSScriptRoot -PassThru
Write-Host "Backend PID: $($backendProcess.Id)" -ForegroundColor Green

# Open frontend in default browser
$frontendUrl = "http://127.0.0.1:$backendPort"
Start-Process $frontendUrl
Write-Host "Frontend opened at $frontendUrl" -ForegroundColor Yellow

# Instructions
Write-Host "`nTo stop Nova Ultimate 2026:"
Write-Host "Stop-Process -Id $($backendProcess.Id) -Force" -ForegroundColor Red