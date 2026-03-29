# =========================================================
# Nova Ultimate 2026 Phase 6
# Quick Rebuild + Zip (Endgame)
# =========================================================

$NovaRoot  = "C:\Users\Owner\nova"
$BuildRoot = "C:\Users\Owner\nova_build_portable"
$ZipPath   = "C:\Users\Owner\nova_portable_phase6.zip"
$PythonExe = "C:\Python311\python.exe"   # Update if needed

# Clean previous build/zip
if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

# Rebuild portable folder
New-Item -ItemType Directory -Path $BuildRoot
Copy-Item "$NovaRoot\*" $BuildRoot -Recurse -Force

# PyInstaller single-file build
Push-Location $BuildRoot
& $PythonExe -m PyInstaller --onefile --add-data "templates;templates" --add-data "static;static" --add-data "data;data" app.py
Pop-Location

# Zip everything for distribution
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($BuildRoot, $ZipPath)

Write-Host "✅ Quick rebuild & zip complete!"
Write-Host "Build folder: $BuildRoot"
Write-Host "Zip package: $ZipPath"