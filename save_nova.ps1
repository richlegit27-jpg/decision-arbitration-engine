$ErrorActionPreference = "Continue"

$ProjectRoot = "C:\Users\Owner\nova"
$BackendRoot = "C:\Users\Owner\nova\backend"
$RoutesRoot = "C:\Users\Owner\nova\backend\routes"
$ServicesRoot = "C:\Users\Owner\nova\backend\services"
$TemplatesRoot = "C:\Users\Owner\nova\templates"
$StaticJsRoot = "C:\Users\Owner\nova\static\js"
$DataRoot = "C:\Users\Owner\nova\data"

$Problems = New-Object System.Collections.Generic.List[string]
$Warnings = New-Object System.Collections.Generic.List[string]

function Add-Problem {
    param([string]$Message)
    $script:Problems.Add($Message) | Out-Null
}

function Add-Warning {
    param([string]$Message)
    $script:Warnings.Add($Message) | Out-Null
}

function Test-RequiredPath {
    param(
        [string]$Path,
        [string]$Label
    )

    if (Test-Path $Path) {
        Write-Host "[OK] $Label" -ForegroundColor Green
        Write-Host "     $Path" -ForegroundColor DarkGray
        return $true
    }

    Write-Host "[MISS] $Label" -ForegroundColor Red
    Write-Host "       $Path" -ForegroundColor DarkGray
    Add-Problem "$Label missing: $Path"
    return $false
}

function Test-FileContains {
    param(
        [string]$Path,
        [string]$Needle,
        [string]$Label
    )

    if (-not (Test-Path $Path)) {
        Add-Problem "$Label skipped because file missing: $Path"
        Write-Host "[MISS] $Label" -ForegroundColor Red
        return
    }

    $Content = Get-Content -Path $Path -Raw -ErrorAction SilentlyContinue

    if ($null -eq $Content) {
        Add-Problem "$Label could not read file: $Path"
        Write-Host "[FAIL] $Label" -ForegroundColor Red
        return
    }

    if ($Content -match [regex]::Escape($Needle)) {
        Write-Host "[OK] $Label" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] $Label" -ForegroundColor Red
        Add-Problem "$Label missing text: $Needle"
    }
}

function Test-PythonImport {
    param([string]$ModuleName)

    try {
        python -c "import $ModuleName; print('ok')" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Python module: $ModuleName" -ForegroundColor Green
        }
        else {
            Write-Host "[FAIL] Python module: $ModuleName" -ForegroundColor Red
            Add-Problem "Python module missing or broken: $ModuleName"
        }
    }
    catch {
        Write-Host "[FAIL] Python module: $ModuleName" -ForegroundColor Red
        Add-Problem "Python module missing or broken: $ModuleName"
    }
}

function Test-EnvVarState {
    param([string]$Name)

    $Value = [Environment]::GetEnvironmentVariable($Name, "Process")

    if ([string]::IsNullOrWhiteSpace($Value)) {
        Write-Host "[WARN] Env var not set in current session: $Name" -ForegroundColor Yellow
        Add-Warning "Env var not set in current session: $Name"
    }
    else {
        Write-Host "[OK] Env var set in current session: $Name" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Nova Preflight Checker" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Test-RequiredPath -Path $ProjectRoot -Label "Project root"
Test-RequiredPath -Path $BackendRoot -Label "Backend root"
Test-RequiredPath -Path $RoutesRoot -Label "Routes folder"
Test-RequiredPath -Path $ServicesRoot -Label "Services folder"
Test-RequiredPath -Path $TemplatesRoot -Label "Templates folder"
Test-RequiredPath -Path $StaticJsRoot -Label "Static JS folder"
Test-RequiredPath -Path $DataRoot -Label "Data folder"

Write-Host ""
Write-Host "Checking core files..." -ForegroundColor Cyan

Test-RequiredPath -Path "C:\Users\Owner\nova\backend\main.py" -Label "main.py"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\db.py" -Label "db.py"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\routes\__init__.py" -Label "routes __init__.py"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\services\__init__.py" -Label "services __init__.py"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\routes\auth.py" -Label "auth route"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\routes\pages.py" -Label "pages route"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\routes\chats.py" -Label "chats route"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\routes\memory.py" -Label "memory route"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\services\auth_service.py" -Label "auth service"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\services\ai_service.py" -Label "ai service"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\services\chat_service.py" -Label "chat service"
Test-RequiredPath -Path "C:\Users\Owner\nova\backend\services\memory_service.py" -Label "memory service"
Test-RequiredPath -Path "C:\Users\Owner\nova\templates\index.html" -Label "index template"
Test-RequiredPath -Path "C:\Users\Owner\nova\templates\login.html" -Label "login template"
Test-RequiredPath -Path "C:\Users\Owner\nova\templates\account.html" -Label "account template"
Test-RequiredPath -Path "C:\Users\Owner\nova\static\js\app.js" -Label "app.js"
Test-RequiredPath -Path "C:\Users\Owner\nova\static\js\composer.js" -Label "composer.js"
Test-RequiredPath -Path "C:\Users\Owner\nova\static\js\memory-panel.js" -Label "memory-panel.js"

Write-Host ""
Write-Host "Checking required route wiring..." -ForegroundColor Cyan

Test-FileContains -Path "C:\Users\Owner\nova\backend\main.py" -Needle "app.include_router(auth_router)" -Label "main.py auth router wired"
Test-FileContains -Path "C:\Users\Owner\nova\backend\main.py" -Needle "app.include_router(chats_router)" -Label "main.py chats router wired"
Test-FileContains -Path "C:\Users\Owner\nova\backend\main.py" -Needle "app.include_router(memory_router)" -Label "main.py memory router wired"
Test-FileContains -Path "C:\Users\Owner\nova\backend\main.py" -Needle "app.include_router(pages_router)" -Label "main.py pages router wired"

Test-FileContains -Path "C:\Users\Owner\nova\backend\routes\chats.py" -Needle '@router.post("/{chat_id}/reply")' -Label "reply route exists"
Test-FileContains -Path "C:\Users\Owner\nova\backend\routes\chats.py" -Needle '@router.post("/{chat_id}/reply-stream")' -Label "reply-stream route exists"
Test-FileContains -Path "C:\Users\Owner\nova\backend\routes\memory.py" -Needle 'router = APIRouter(prefix="/api/memory"' -Label "memory router prefix exists"
Test-FileContains -Path "C:\Users\Owner\nova\static\js\composer.js" -Needle "/reply-stream" -Label "composer uses reply-stream"
Test-FileContains -Path "C:\Users\Owner\nova\static\js\memory-panel.js" -Needle "/api/memory" -Label "memory panel uses backend memory"
Test-FileContains -Path "C:\Users\Owner\nova\templates\index.html" -Needle 'id="sendBtn"' -Label "index has send button"
Test-FileContains -Path "C:\Users\Owner\nova\templates\index.html" -Needle 'id="messageInput"' -Label "index has message input"
Test-FileContains -Path "C:\Users\Owner\nova\templates\index.html" -Needle 'id="chatMessages"' -Label "index has chat messages container"

Write-Host ""
Write-Host "Checking Python modules..." -ForegroundColor Cyan

Test-PythonImport -ModuleName "fastapi"
Test-PythonImport -ModuleName "uvicorn"
Test-PythonImport -ModuleName "jinja2"
Test-PythonImport -ModuleName "openai"
Test-PythonImport -ModuleName "multipart"

Write-Host ""
Write-Host "Checking env state..." -ForegroundColor Cyan

Test-EnvVarState -Name "OPENAI_API_KEY"
Test-EnvVarState -Name "NOVA_MODEL"

Write-Host ""
Write-Host "Checking SQLite DB..." -ForegroundColor Cyan

$DbPath = "C:\Users\Owner\nova\data\nova.db"
if (Test-Path $DbPath) {
    Write-Host "[OK] SQLite DB exists" -ForegroundColor Green
    Write-Host "     $DbPath" -ForegroundColor DarkGray
}
else {
    Write-Host "[WARN] SQLite DB not found yet" -ForegroundColor Yellow
    Add-Warning "SQLite DB not found yet: $DbPath"
}

Write-Host ""
Write-Host "Checking server import..." -ForegroundColor Cyan

try {
    Push-Location $BackendRoot
    python -c "import main; print('main import ok')" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] backend main.py imports cleanly" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] backend main.py import failed" -ForegroundColor Red
        Add-Problem "backend main.py import failed"
    }
}
catch {
    Write-Host "[FAIL] backend main.py import failed" -ForegroundColor Red
    Add-Problem "backend main.py import failed: $($_.Exception.Message)"
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Preflight Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

if ($Warnings.Count -gt 0) {
    Write-Host "Warnings:" -ForegroundColor Yellow
    foreach ($Warning in $Warnings) {
        Write-Host " - $Warning" -ForegroundColor Yellow
    }
    Write-Host ""
}

if ($Problems.Count -gt 0) {
    Write-Host "Problems found:" -ForegroundColor Red
    foreach ($Problem in $Problems) {
        Write-Host " - $Problem" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Preflight FAILED." -ForegroundColor Red
    Pause
    exit 1
}

Write-Host "Preflight PASSED." -ForegroundColor Green
Write-Host ""
Pause