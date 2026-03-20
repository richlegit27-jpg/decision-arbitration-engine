# Launch Nova frontend + backend (dynamic ports) - smff ready

# ----------------------------
# 1️⃣ Set dynamic ports
# ----------------------------
$backendPort = Get-Random -Minimum 8740 -Maximum 8799
$frontendPort = Get-Random -Minimum 8800 -Maximum 8850

Write-Host "Backend will run on port: $backendPort" -ForegroundColor Cyan
Write-Host "Frontend will run on port: $frontendPort" -ForegroundColor Cyan

# ----------------------------
# 2️⃣ Start FastAPI backend
# ----------------------------
$backendScript = "C:\Users\Owner\nova\nova_app.py"
$backendProcess = Start-Process -FilePath python -ArgumentList "$backendScript --port $backendPort" -PassThru
Start-Sleep -Seconds 2

Write-Host "Backend started (PID: $($backendProcess.Id))" -ForegroundColor Green

# ----------------------------
# 3️⃣ Start simple HTTP frontend server
# ----------------------------
$frontendDir = "C:\Users\Owner\nova\templates"
$frontendProcess = Start-Process -FilePath python -ArgumentList "-m http.server $frontendPort --directory `"$frontendDir`"" -PassThru
Start-Sleep -Seconds 2

Write-Host "Frontend started (PID: $($frontendProcess.Id))" -ForegroundColor Green

# ----------------------------
# 4️⃣ Open browser automatically
# ----------------------------
$frontendURL = "http://127.0.0.1:$frontendPort"
Write-Host "Opening Nova frontend at $frontendURL" -ForegroundColor Yellow
Start-Process $frontendURL

# ----------------------------
# 5️⃣ Cleanup instructions
# ----------------------------
Write-Host "To stop Nova, run: Stop-Process -Id $($backendProcess.Id) -Force" -ForegroundColor Red
Write-Host "                  Stop-Process -Id $($frontendProcess.Id) -Force" -ForegroundColor Red