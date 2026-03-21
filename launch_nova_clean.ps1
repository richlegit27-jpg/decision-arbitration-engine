# --- Step 1: Kill all old Python servers ---
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

# --- Step 2: Clear __pycache__ ---
Write-Host "`n=== Clearing Python cache ===" -ForegroundColor Cyan
Get-ChildItem -Path "C:\Users\Owner\nova" -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
    Write-Host "Removed: $($_.FullName)" -ForegroundColor Green
}

# --- Step 3: Start FastAPI Uvicorn server ---
Write-Host "`n=== Starting Nova FastAPI server ===" -ForegroundColor Cyan
cd C:\Users\Owner\nova

py -m uvicorn nova_app:app --reload --port 8750