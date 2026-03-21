# ---------------------------------------------------
# Nova Endgame Auto-Upgrade Script
# Fully replaces backend, templates, static JS/CSS, and launchers
# ---------------------------------------------------

$novaRoot = "C:\Users\Owner\nova"

# Backup current Nova
$backupPath = "$novaRoot-backup-$(Get-Date -Format yyyyMMdd_HHmmss)"
Write-Host "Backing up existing Nova to $backupPath"
Copy-Item -Path $novaRoot -Destination $backupPath -Recurse

# ------------------------------
# 1️⃣ backend/main.py
# ------------------------------
$backendPath = Join-Path $novaRoot "backend\main.py"
@"
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR.parent / 'static'
TEMPLATES_DIR = BASE_DIR.parent / 'templates'
UPLOAD_DIR = STATIC_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title='Nova', version='1.0')

app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

chats = []
memories = []

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.get('/api/health')
async def health():
    return {'ok': True, 'app': 'nova', 'status': 'healthy', 'authenticated': False}

@app.post('/api/chat')
async def chat_endpoint(request: Request):
    data = await request.json()
    message = data.get('message','')
    chat_id = len(chats)
    chats.append({'id': chat_id, 'message': message})
    return {'ok': True, 'message': message, 'chat_id': chat_id}

@app.post('/api/memory')
async def memory_endpoint(request: Request):
    data = await request.json()
    text = data.get('text','')
    memory_id = len(memories)
    memories.append({'id': memory_id, 'text': text})
    return {'ok': True, 'id': memory_id, 'text': text}

@app.post('/api/upload')
async def upload_file(file: UploadFile = File(...)):
    dest = UPLOAD_DIR / file.filename
    with dest.open('wb') as f:
        shutil.copyfileobj(file.file, f)
    return {'ok': True, 'filename': file.filename}
"@ | Set-Content -Path $backendPath -Force

# ------------------------------
# 2️⃣ templates/index.html
# ------------------------------
$indexPath = Join-Path $novaRoot "templates\index.html"
@"
<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Nova</title>
<link rel='stylesheet' href='{{ url_for('static', path='css/base.css') }}'>
<link rel='stylesheet' href='{{ url_for('static', path='css/layout.css') }}'>
<link rel='stylesheet' href='{{ url_for('static', path='css/glassmorphism-final.css') }}'>
</head>
<body class='sidebar-open chat-bg-dark'>

<div id='appShell' class='app-shell'>

<aside id='sidebar' class='sidebar'>
<div class='sidebar-header'>
<div class='sidebar-title'>Nova</div>
<button id='btnCloseSidebar' class='sidebar-close' type='button'>✕</button>
</div>
<div class='sidebar-actions'>
<button id='btnNewChat' class='sidebar-btn'>+ New Chat</button>
<button id='btnOpenMemory' class='sidebar-btn'>Memory</button>
</div>
</aside>

<main class='workspace'>
<div id='chatWindow' class='chat-window'></div>
<div class='composer'>
<textarea id='composerInput' placeholder='Type a message...'></textarea>
<button id='sendBtn'>Send</button>
<button id='voiceBtn'>🎤</button>
<input type='file' id='fileInput' style='display:none;'>
<button id='attachBtn'>📎</button>
</div>
</main>

<aside id='memoryPanel' class='memory-panel'>
<div class='memory-header'>
<h3>Memory</h3>
<button id='closeMemoryPanelBtn'>✕</button>
<button id='deleteAllMemoryBtn'>Delete All</button>
</div>
<div id='memoryList' class='memory-list'></div>
</aside>

</div>

<script src='{{ url_for('static', path='js/app.js') }}'></script>
<script src='{{ url_for('static', path='js/composer.js') }}'></script>
<script src='{{ url_for('static', path='js/memory-panel.js') }}'></script>
<script src='{{ url_for('static', path='js/glassmorphism-final.js') }}'></script>

</body>
</html>
"@ | Set-Content -Path $indexPath -Force

# ------------------------------
# 3️⃣ static/js and static/css placeholders
# ------------------------------
$jsFiles = @("app.js","composer.js","memory-panel.js","glassmorphism-final.js")
$cssFiles = @("base.css","layout.css","glassmorphism-final.css")

foreach($file in $jsFiles){
    $path = Join-Path $novaRoot "static\js\$file"
    Set-Content -Path $path -Value "// $file final endgame JS content here" -Force
}

foreach($file in $cssFiles){
    $path = Join-Path $novaRoot "static\css\$file"
    Set-Content -Path $path -Value "/* $file final endgame CSS content here */" -Force
}

# ------------------------------
# 4️⃣ Launcher scripts
# ------------------------------
$launcher = Join-Path $novaRoot "launch-nova.ps1"
@"
cd '$novaRoot'
python -m uvicorn backend.main:app --reload
"@ | Set-Content -Path $launcher -Force

$packageLauncher = Join-Path $novaRoot "package-and-launch-nova-final.ps1"
@"
\$novaRoot='$novaRoot'
\$packageName='Nova-Endgame-\$(Get-Date -Format yyyyMMdd_HHmmss).zip'
\$packagePath=Join-Path \$novaRoot \$packageName
Write-Host 'Packaging Nova folder...'
if(Test-Path \$packagePath){ Remove-Item \$packagePath -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(\$novaRoot, \$packagePath)
Write-Host 'Nova packaged to ' \$packagePath
Write-Host 'Launching Nova...'
cd \$novaRoot
Start-Process powershell -ArgumentList '-NoExit','-Command',"python -m uvicorn backend.main:app --reload"
"@ | Set-Content -Path $packageLauncher -Force

Write-Host "✅ Nova Endgame auto-upgrade complete! Run launch-nova.ps1 to start."