# --- Step 1: Kill all old Python processes ---
Write-Host "`n=== Stopping old Python servers ===" -ForegroundColor Cyan
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | ForEach-Object {
        Write-Host "Stopping process Id $($_.Id)" -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force
    }
} else {
    Write-Host "No Python processes running." -ForegroundColor Green
}

# --- Step 2: Start FastAPI Uvicorn server ---
Write-Host "`n=== Starting Nova FastAPI server ===" -ForegroundColor Cyan
cd C:\Users\Owner\nova

# Launch uvicorn and wait
py -m uvicorn app:app --reload --port 8743