param(
    [switch]$SkipGit
)

$ErrorActionPreference = "Stop"

$Root = "C:\Users\Owner\nova"
$Smoke = Join-Path $Root "tools\nova_public_smoke.py"

Write-Host ""
Write-Host "NOVA PUBLIC RELEASE CHECK" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host ""

if (!(Test-Path $Smoke)) {
    Write-Host "Missing smoke script: $Smoke" -ForegroundColor Red
    exit 1
}

Push-Location $Root

try {
    Write-Host "Running public smoke test..." -ForegroundColor Cyan
    python $Smoke

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Public smoke failed." -ForegroundColor Red
        exit $LASTEXITCODE
    }

    if (!$SkipGit) {
        Write-Host ""
        Write-Host "Checking staged files for accidental mobile changes..." -ForegroundColor Cyan

        $cached = git diff --cached --name-only
        $mobileCached = $cached | Select-String -Pattern "mobile"

        if ($mobileCached) {
            Write-Host ""
            Write-Host "Blocked: staged mobile files detected." -ForegroundColor Red
            $mobileCached
            exit 1
        }

        Write-Host ""
        Write-Host "Current git status:" -ForegroundColor Cyan
        git status --short
    }

    Write-Host ""
    Write-Host "NOVA PUBLIC RELEASE CHECK PASSED" -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
}
