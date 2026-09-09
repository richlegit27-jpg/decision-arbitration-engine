\C:\Users\Owner\nova='C:\Users\Owner\nova'
\='Nova-Endgame-\20260907_044645.zip'
\=Join-Path \C:\Users\Owner\nova \

Write-Host 'Packaging Nova folder...'
if(Test-Path \){ Remove-Item \ -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(\C:\Users\Owner\nova, \)
Write-Host 'Nova packaged to ' \

Write-Host 'Launching Nova...'
cd \C:\Users\Owner\nova
Start-Process powershell -ArgumentList '-NoExit','-Command',"python -m uvicorn backend.main:app --reload"
