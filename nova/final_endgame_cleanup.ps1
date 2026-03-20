# --------------------------------------------
# Nova Endgame Final Copy Minimal Cleanup
# --------------------------------------------

$sourcePath = "C:\Users\Owner\nova_endgame_source"

Write-Host "Cleaning up nova_endgame_source to keep only essential files..."

# -----------------------------
# Templates: keep only index.html and active HTML files
# -----------------------------
$templatesPath = Join-Path $sourcePath "templates"
Get-ChildItem -Path $templatesPath -File | Where-Object {
    $_.Name -notin @("index.html","login.html","register.html","final_chat_interface.html")
} | Remove-Item -Force

# -----------------------------
# Static CSS: keep only base.css and layout.css
# -----------------------------
$cssPath = Join-Path $sourcePath "static\css"
Get-ChildItem -Path $cssPath -File | Where-Object {
    $_.Name -notin @("base.css","layout.css")
} | Remove-Item -Force

# -----------------------------
# Static JS: keep only core JS files
# -----------------------------
$jsPath = Join-Path $sourcePath "static\js"
Get-ChildItem -Path $jsPath -File | Where-Object {
    $_.Name -notin @("app.js","composer.js","memory-panel.js")
} | Remove-Item -Force

Write-Host "✅ Minimal cleanup complete. Only essential working files remain."