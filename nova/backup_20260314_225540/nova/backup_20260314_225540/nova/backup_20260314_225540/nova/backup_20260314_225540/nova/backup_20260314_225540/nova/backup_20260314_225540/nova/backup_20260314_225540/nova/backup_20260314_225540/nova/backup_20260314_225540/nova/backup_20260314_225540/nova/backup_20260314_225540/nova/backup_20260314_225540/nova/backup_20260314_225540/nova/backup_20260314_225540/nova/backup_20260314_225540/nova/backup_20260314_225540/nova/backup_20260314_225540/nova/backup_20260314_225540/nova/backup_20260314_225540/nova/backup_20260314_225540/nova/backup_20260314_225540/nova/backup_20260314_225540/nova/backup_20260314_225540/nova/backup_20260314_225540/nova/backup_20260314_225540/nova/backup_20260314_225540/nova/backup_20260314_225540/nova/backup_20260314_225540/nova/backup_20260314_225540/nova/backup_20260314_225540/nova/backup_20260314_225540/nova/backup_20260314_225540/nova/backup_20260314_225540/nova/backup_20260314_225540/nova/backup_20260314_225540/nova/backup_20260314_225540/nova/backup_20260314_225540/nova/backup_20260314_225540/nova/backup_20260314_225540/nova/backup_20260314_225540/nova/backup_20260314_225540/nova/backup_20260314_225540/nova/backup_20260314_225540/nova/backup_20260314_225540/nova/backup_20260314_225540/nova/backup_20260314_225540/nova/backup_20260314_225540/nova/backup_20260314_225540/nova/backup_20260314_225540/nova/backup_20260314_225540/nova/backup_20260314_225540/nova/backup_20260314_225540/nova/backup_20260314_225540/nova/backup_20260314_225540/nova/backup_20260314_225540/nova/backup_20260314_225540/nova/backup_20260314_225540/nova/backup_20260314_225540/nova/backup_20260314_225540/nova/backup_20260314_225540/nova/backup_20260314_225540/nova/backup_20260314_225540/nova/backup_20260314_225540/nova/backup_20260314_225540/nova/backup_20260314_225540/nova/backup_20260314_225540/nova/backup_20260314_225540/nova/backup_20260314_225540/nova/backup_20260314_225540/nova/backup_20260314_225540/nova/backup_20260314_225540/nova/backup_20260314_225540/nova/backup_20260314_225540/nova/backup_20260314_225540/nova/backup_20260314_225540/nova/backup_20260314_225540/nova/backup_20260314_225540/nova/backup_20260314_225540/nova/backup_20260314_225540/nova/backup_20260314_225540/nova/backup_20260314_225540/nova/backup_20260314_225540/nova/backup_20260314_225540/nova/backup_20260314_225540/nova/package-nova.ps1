# -------------------------------
# Nova Endgame Packaging Script
# -------------------------------

# Source folder: the Nova-Endgame folder
$sourceFolder = "C:\Users\Owner\nova"

# Output folder for zips
$outputFolder = "C:\Users\Owner"
if (-not (Test-Path $outputFolder)) {
    New-Item -ItemType Directory -Path $outputFolder | Out-Null
}

# Zip file name with timestamp
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipFile = Join-Path $outputFolder "Nova-Endgame-$timestamp.zip"

# Remove existing zip if it exists
if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

# Create zip
Compress-Archive -Path "$sourceFolder\*" -DestinationPath $zipFile -Force

Write-Host "Nova packaged successfully!"
Write-Host "Zip file created at: $zipFile"