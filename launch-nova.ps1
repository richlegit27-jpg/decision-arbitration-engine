# -------------------------------
# Nova Endgame Launch Script
# -------------------------------

# Navigate to Nova directory
Set-Location "C:\Users\Owner\nova"

# Ensure uploads folder exists
$uploadDir = ".\static\uploads"
if (-not (Test-Path $uploadDir)) {
    New-Item -ItemType Directory -Path $uploadDir | Out-Null
    Write-Host "Created uploads directory at $uploadDir"
} else {
    Write-Host "Uploads directory exists."
}

# Start FastAPI backend
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