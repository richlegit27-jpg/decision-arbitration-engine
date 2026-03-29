# =========================================================
# Nova Ultimate 2026 Phase 6
# Endgame Portable Zip Builder
# =========================================================

$NovaRoot  = "C:\Users\Owner\nova"
$BuildRoot = "C:\Users\Owner\nova_phase6_portable"
$ZipPath   = "C:\Users\Owner\nova_phase6_endgame.zip"
$PythonExe = "C:\Python311\python.exe"  # Update if needed

# 1. Clean previous build/zip
if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

# 2. Copy nova files into portable build folder
New-Item -ItemType Directory -Path $BuildRoot
Copy-Item "$NovaRoot\templates" "$BuildRoot\templates" -Recurse
Copy-Item "$NovaRoot\static" "$BuildRoot\static" -Recurse
Copy-Item "$NovaRoot\app.py" "$BuildRoot\app.py"
Copy-Item "$NovaRoot\services" "$BuildRoot\services" -Recurse
Copy-Item "$NovaRoot\data" "$BuildRoot\data" -Recurse

# Optional: include README or checklist
Copy-Item "$NovaRoot\PHASE6_LAUNCH_CHECKLIST.txt" $BuildRoot -ErrorAction SilentlyContinue

# 3. Build standalone executable via PyInstaller
Push-Location $BuildRoot
& $PythonExe -m PyInstaller --onefile --add-data "templates;templates" --add-data "static;static" --add-data "data;data" app.py
Pop-Location

# 4. Zip the entire portable build
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($BuildRoot, $ZipPath)

Write-Host "✅ Phase 6 Endgame Portable Build Complete!"
Write-Host "Build folder: $BuildRoot"
Write-Host "Zip file: $ZipPath"