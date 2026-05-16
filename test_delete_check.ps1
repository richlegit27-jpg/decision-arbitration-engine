$base = "http://127.0.0.1:8000"

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

Write-Host "1. Log in first in browser, then copy cookies if needed." -ForegroundColor Yellow
Write-Host "2. If your browser session already works in app, frontend JS is the more likely problem." -ForegroundColor Yellow

try {
    $memory = Invoke-RestMethod -Uri "$base/api/memory" -Method GET -WebSession $session
    $memory | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Memory GET failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

try {
    $chats = Invoke-RestMethod -Uri "$base/api/chats" -Method GET -WebSession $session
    $chats | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Chats GET failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message
}