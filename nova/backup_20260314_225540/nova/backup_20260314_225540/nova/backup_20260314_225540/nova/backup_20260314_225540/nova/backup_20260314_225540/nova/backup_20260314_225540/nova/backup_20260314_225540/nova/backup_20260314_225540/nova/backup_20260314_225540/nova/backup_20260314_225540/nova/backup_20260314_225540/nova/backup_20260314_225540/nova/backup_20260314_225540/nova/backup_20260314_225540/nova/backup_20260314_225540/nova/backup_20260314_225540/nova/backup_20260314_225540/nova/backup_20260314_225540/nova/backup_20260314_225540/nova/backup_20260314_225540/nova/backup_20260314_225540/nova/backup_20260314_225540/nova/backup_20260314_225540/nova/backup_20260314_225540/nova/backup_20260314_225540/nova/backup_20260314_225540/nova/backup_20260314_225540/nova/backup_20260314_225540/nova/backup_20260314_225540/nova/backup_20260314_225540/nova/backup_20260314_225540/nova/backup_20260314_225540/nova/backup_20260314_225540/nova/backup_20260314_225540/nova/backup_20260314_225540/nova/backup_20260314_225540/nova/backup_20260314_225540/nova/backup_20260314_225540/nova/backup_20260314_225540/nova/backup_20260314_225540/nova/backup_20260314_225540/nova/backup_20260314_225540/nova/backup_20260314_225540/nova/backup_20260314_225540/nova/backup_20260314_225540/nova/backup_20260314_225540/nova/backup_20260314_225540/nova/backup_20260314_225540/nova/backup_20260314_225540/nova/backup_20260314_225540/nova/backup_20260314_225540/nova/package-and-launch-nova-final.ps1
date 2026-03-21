# ---------------------------------------------------
# Nova Endgame: Package & Launch Script
# ---------------------------------------------------

$novaRoot = "C:\Users\Owner\nova"
$packageName = "Nova-Endgame-$(Get-Date -Format yyyyMMdd_HHmmss).zip"
$packagePath = Join-Path $novaRoot $packageName

Write-Host "Packaging Nova folder..."

# Remove existing zip if it exists
if(Test-Path $packagePath){ Remove-Item $packagePath -Force }

# Create zip
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($novaRoot, $packagePath)

Write-Host "Nova packaged to $packagePath"

# Optional: Launch Nova
Write-Host "Launching Nova..."
cd $novaRoot
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn backend.main:app --reload"

Write-Host "Nova should now be running at http://127.0.0.1:8000/"