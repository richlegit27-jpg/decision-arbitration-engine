# -------------------------------
# Nova Endgame Package + Launch
# -------------------------------

# Source folder: Nova folder
$sourceFolder = "C:\Users\Owner\nova"

# Output folder for zip
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

# Ensure uploads folder exists
$uploadDir = Join-Path $sourceFolder "static\uploads"
if (-not (Test-Path $uploadDir)) {
    New-Item -ItemType Directory -Path $uploadDir | Out-Null
    Write-Host "Created uploads directory at $uploadDir"
} else {
    Write-Host "Uploads directory exists."
}

# Launch Nova backend
Write-Host "Starting Nova backend..."
Start-Process powershell -ArgumentList "uvicorn backend.main:app --reload --port 8000"

# Wait a few seconds for server to start
Start-Sleep -Seconds 3

# Check health endpoint
try {
    $response = Invoke-RestMethod -Uri http://127.0.0.1:8000/health
    if ($response.status -eq "healthy") {
        Write-Host "Nova backend is healthy and running!"
    } else {
        Write-Host "Nova backend started, but health check returned unexpected result."
    }
} catch {
    Write-Host "Unable to reach Nova backend. Make sure uvicorn is installed and path is correct."
}

Write-Host "`nNova is packaged and running. Open http://127.0.0.1:8000/ to use Nova."