# ---------------------------------------------------
# Nova Endgame: Fully Bundled ZIP Creator
# ---------------------------------------------------

$novaRoot = "C:\Users\Owner\nova"
$timestamp = Get-Date -Format yyyyMMdd_HHmmss
$packageName = "Nova-Endgame-$timestamp.zip"
$packagePath = Join-Path $novaRoot $packageName

Write-Host "Creating ZIP package for Nova Endgame..."
if(Test-Path $packagePath){ Remove-Item $packagePath -Force }

# Load Compression library
Add-Type -AssemblyName System.IO.Compression.FileSystem

# Create ZIP of entire Nova folder
[System.IO.Compression.ZipFile]::CreateFromDirectory($novaRoot, $packagePath)

Write-Host "✅ Nova packaged successfully: $packagePath"

# Optional: launch Nova automatically after packaging
Write-Host "Launching Nova..."
cd $novaRoot
Start-Process powershell -ArgumentList "-NoExit","-Command","python -m uvicorn backend.main:app --reload"

Write-Host "Nova is running at http://127.0.0.1:8000/"