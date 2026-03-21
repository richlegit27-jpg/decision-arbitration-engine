$zipPath="C:\Users\Owner\nova-endgame\nova-deploy-ready.zip"
$deployFolder="C:\Users\Owner\nova"
Expand-Archive -Path $zipPath -DestinationPath $deployFolder -Force
cd "$deployFolder\backend"
Start-Process "powershell" -ArgumentList "uvicorn main:app --reload --port 8000"
Start-Process "http://127.0.0.1:8000/"
Write-Host "✅ Nova deployed. Paste stress-test.js in browser console to verify."