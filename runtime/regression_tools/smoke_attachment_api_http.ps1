param(
    [string]$BaseUrl = "https://decision-arbitration-engine-production.up.railway.app"
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
Write-Host "NOVA ATTACHMENT API HTTP SMOKE"
Write-Host "=============================="
Write-Host "BaseUrl: $BaseUrl"
Write-Host ""

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("nova-attachment-http-smoke-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$tempFile = Join-Path $tempDir "attachment-api-http-smoke.txt"
$marker = "ATTACHMENT_HTTP_SMOKE_PURPLE_ROBOT_20260705"

Set-Content -Path $tempFile -Value "This is a Nova attachment HTTP smoke test. Marker: $marker. The assistant must mention this exact marker from the attached file." -Encoding UTF8

try {
    Write-Host "1. Uploading test file..."

    $upload = Invoke-NovaUploadFile -BaseUrl $BaseUrl -FilePath $tempFile

    Write-Host ""
    Write-Host "Upload response:"
    $upload | ConvertTo-Json -Depth 30

    if ($upload.ok -eq $false) {
        throw "Upload returned ok=false"
    }

    if (-not ($upload.filename -or $upload.name -or $upload.url -or $upload.path)) {
        throw "Upload response is missing usable attachment identity fields."
    }

    Write-Host ""
    Write-Host "2. Sending uploaded attachment into /api/chat..."

    $payload = @{
        session_id = "session_attachment_http_smoke_20260705"
        sessionId = "session_attachment_http_smoke_20260705"
        message = "Summarize this attached file. Mention the exact marker if you can see it."
        text = "Summarize this attached file. Mention the exact marker if you can see it."
        user_text = "Summarize this attached file. Mention the exact marker if you can see it."
        attachments = @($upload)
        files = @($upload)
    }

    $chat = Invoke-RestMethod `
        -Uri "$BaseUrl/api/chat" `
        -Method POST `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 50)

    Write-Host ""
    Write-Host "Chat response:"
    $chat | ConvertTo-Json -Depth 50

    $chatText = ($chat | ConvertTo-Json -Depth 50)

    Write-Host ""
    Write-Host "3. Checking attachment marker..."

    if ($chatText -notmatch [regex]::Escape($marker)) {
        throw "FAIL: chat response did not mention marker. Attachment context may not be reaching chat."
    }

    Write-Host "PASS: chat response mentioned marker."

    if ($chatText -match "No verified fresh web results|verified fresh web|DuckDuckGo|Google News|web results|search fallback") {
        throw "FAIL: chat response appears to have used web/search fallback wording."
    }

    Write-Host "PASS: no web fallback wording detected."

    Write-Host ""
    Write-Host "ATTACHMENT API HTTP SMOKE PASSED."
} finally {
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
}
