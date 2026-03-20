cd C:\Users\Owner\nova

try { python --version | Out-Null } catch { Write-Host "Python not found!" -ForegroundColor Red; exit }

$flaskInstalled = python -m pip show flask
if (-not $flaskInstalled) { Write-Host "Installing Flask..."; python -m pip install flask }

Start-Process powershell -ArgumentList "-NoExit", "-Command", "python nova_app.py"

Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:8743/"
Write-Host "Nova launch sequence complete!" -ForegroundColor Green