param(
    [string]$BaseUrl = "http://127.0.0.1:5001"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BaseUrl = $BaseUrl.TrimEnd("/")

function Invoke-NovaUploadFile {
    param(
        [string]$BaseUrl,
        [string]$FilePath
    )

    $uploadUrl = "$BaseUrl/api/upload"

    $raw = & curl.exe -sS -X POST -F "file=@$FilePath;type=text/plain" $uploadUrl

    if ($LASTEXITCODE -ne 0) {
        throw "curl upload failed with exit code $LASTEXITCODE"
    }

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "Upload returned empty response."
    }

    return $raw | ConvertFrom-Json
}

Write-Host ""
Write-Host "NOVA LIVE UPLOAD -> CHAT SMOKE"
Write-Host "=============================="
Write-Host "BaseUrl: $BaseUrl"
Write-Host ""

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("nova-live-attach-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$tempFile = Join-Path $tempDir "live-upload-chat-smoke.txt"

$marker = "LIVE_ATTACHMENT_MARKER_PURPLE_ROBOT_20260705"
Set-Content -Path $tempFile -Value "This is a Nova live attachment smoke test. Marker: $marker. The assistant should mention the purple robot marker and should not search the web." -Encoding UTF8

try {
    Write-Host "1. Uploading file..."

    $upload = Invoke-NovaUploadFile -BaseUrl $BaseUrl -FilePath $tempFile

    Write-Host "Upload response:"
    $upload | ConvertTo-Json -Depth 20

    if ($upload.ok -eq $false) {
        throw "Upload returned ok=false"
    }

    if (-not ($upload.filename -or $upload.name)) {
        throw "Upload response missing filename/name"
    }

    Write-Host ""
    Write-Host "2. Sending upload JSON into /api/chat..."

    $payload = @{
        session_id = "session_live_upload_to_chat_smoke_20260705"
        message = "Summarize this attached file. Mention the exact marker if you can see it."
        attachments = @(
            $upload
        )
    }

    $chat = Invoke-RestMethod `
        -Uri "$BaseUrl/api/chat" `
        -Method POST `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 30)

    Write-Host ""
    Write-Host "Chat response:"
    $chat | ConvertTo-Json -Depth 30

    $chatText = ($chat | ConvertTo-Json -Depth 30)

    Write-Host ""
    Write-Host "3. Checking marker in response..."

    if ($chatText -match $marker) {
        Write-Host "PASS: chat response mentioned marker."
    } else {
        Write-Host "WARNING: chat response did not mention marker."
        Write-Host "This may mean the model summarized indirectly, or the route still did not use attachment context."
    }

    if ($chatText -match "web|search|internet|No verified fresh web results") {
        Write-Host "WARNING: response contains web/search wording. Inspect output."
    } else {
        Write-Host "PASS: no obvious web fallback wording."
    }

    Write-Host ""
    Write-Host "Live upload -> chat smoke completed."
} finally {
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
}
