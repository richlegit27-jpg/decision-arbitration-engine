# =========================================================
# Nova Ultimate 2026 Phase 6
# Portable Build Script
# =========================================================

# Paths
$NovaRoot      = "C:\Users\Owner\nova"
$BuildRoot     = "C:\Users\Owner\nova_build_portable"
$PythonExe     = "C:\Python311\python.exe"    # Update to your Python path if needed
$PyInstaller   = "pyinstaller"

# Clean previous build
if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }

# Create build folder
New-Item -ItemType Directory -Path $BuildRoot

# Copy static and templates
Copy-Item "$NovaRoot\static" "$BuildRoot\static" -Recurse
Copy-Item "$NovaRoot\templates" "$BuildRoot\templates" -Recurse
Copy-Item "$NovaRoot\data" "$BuildRoot\data" -Recurse

# Copy main backend files
Copy-Item "$NovaRoot\app.py" $BuildRoot
Copy-Item "$NovaRoot\services" "$BuildRoot\services" -Recurse

# Optional: include README, checklist
Copy-Item "$NovaRoot\README.md" $BuildRoot -ErrorAction SilentlyContinue
Copy-Item "$NovaRoot\PHASE6_LAUNCH_CHECKLIST.txt" $BuildRoot -ErrorAction SilentlyContinue

# Build standalone executable with PyInstaller
Write-Host "Building standalone Nova executable..."
Push-Location $BuildRoot

& $PythonExe -m PyInstaller `
    --onefile `
    --add-data "templates;templates" `
    --add-data "static;static" `
    --add-data "data;data" `
    app.py

Pop-Location

# Optional: zip the portable build
$ZipPath = "C:\Users\Owner\nova_portable_phase6.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($BuildRoot, $ZipPath)

Write-Host "âœ… Nova Phase 6 portable build complete!"
Write-Host "Build folder: $BuildRoot"
Write-Host "Zip package: $ZipPath"
