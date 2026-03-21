Set-Location C:\Users\Owner\nova

Write-Host ""
Write-Host "=== NOVA LAUNCH ===" -ForegroundColor Cyan
Write-Host ""

py C:\Users\Owner\nova\make_restore_point.py
if($LASTEXITCODE -ne 0){
    Write-Host "restore point creation failed" -ForegroundColor Red
    exit 1
}

py -m ensurepip --upgrade
if($LASTEXITCODE -ne 0){
    Write-Host "ensurepip failed" -ForegroundColor Red
    exit 1
}

py -m pip install --upgrade pip
if($LASTEXITCODE -ne 0){
    Write-Host "pip upgrade failed" -ForegroundColor Red
    exit 1
}

py -m pip install -r C:\Users\Owner\nova\requirements.txt
if($LASTEXITCODE -ne 0){
    Write-Host "requirements install failed" -ForegroundColor Red
    exit 1
}

py -c "import backend.main; print('backend.main OK')"
if($LASTEXITCODE -ne 0){
    Write-Host "backend.main import failed" -ForegroundColor Red
    exit 1
}

py C:\Users\Owner\nova\start_nova.py