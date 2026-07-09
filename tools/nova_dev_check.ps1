Write-Host ""
Write-Host "NOVA DEV CHECK" -ForegroundColor Cyan
Write-Host "=============================="

Write-Host ""
Write-Host "1. Git status" -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "2. Full check" -ForegroundColor Yellow
python .\tools\nova_full_check.py

Write-Host ""
Write-Host "Done."
Write-Host "If FULL CHECK says PASS and git is clean/expected, Nova core is safe."
