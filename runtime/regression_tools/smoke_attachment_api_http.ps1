param(
    [string]$BaseUrl = "http://127.0.0.1:5001"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BaseUrl = $BaseUrl.TrimEnd("/")

Write-Host ""
Write-Host "NOVA ATTACHMENT API HTTP SMOKE"
Write-Host "=============================="
Write-Host "BaseUrl: $BaseUrl"

function Invoke-NovaJson {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [int[]]$AllowedStatus = @(200)
    )

    $uri = "$BaseUrl$Path"

    try {
        if ($null -eq $Body) {
            $response = Invoke-WebRequest -Uri $uri -Method $Method -UseBasicParsing
        } else {
            $json = $Body | ConvertTo-Json -Depth 20
            $response = Invoke-WebRequest `
                -Uri $uri `
                -Method $Method `
                -ContentType "application/json" `
                -Body $json `
                -UseBasicParsing
        }

        $status = [int]$response.StatusCode
        $raw = [string]$response.Content
    } catch {
        if (-not $_.Exception.Response) {
            throw
        }

        $response = $_.Exception.Response
        $status = [int]$response.StatusCode

        $stream = $response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $raw = $reader.ReadToEnd()
    }

    if ($AllowedStatus -notcontains $status) {
        throw "Unexpected status for $Method $Path`: $status`n$raw"
    }

    $jsonObj = @{}

    if (![string]::IsNullOrWhiteSpace($raw)) {
        $jsonObj = $raw | ConvertFrom-Json
    }

    return @{
        status = $status
        json = $jsonObj
        raw = $raw
    }
}

Write-Host ""
Write-Host "1. Health check..."
$health = Invoke-NovaJson -Method "GET" -Path "/api/health" -AllowedStatus @(200, 503)

Write-Host "Health status: $($health.status)"
Write-Host "attachment_pipeline_ready: $($health.json.attachment_pipeline_ready)"
Write-Host "attachment_debug_routes_require_env: $($health.json.attachment_debug_routes_require_env)"

if ($null -eq $health.json.attachment_pipeline) {
    throw "/api/health is missing attachment_pipeline"
}

Write-Host ""
Write-Host "2. Attachment status check..."
$status = Invoke-NovaJson -Method "GET" -Path "/api/attachment/status" -AllowedStatus @(200)

Write-Host "Status route ready: $($status.json.ready)"

if ($status.json.ok -ne $true) {
    throw "/api/attachment/status did not return ok=true"
}

if ($null -eq $status.json.attachment_pipeline) {
    throw "/api/attachment/status is missing attachment_pipeline"
}

Write-Host ""
Write-Host "3. Debug route disabled by default..."
$debug = Invoke-NovaJson `
    -Method "POST" `
    -Path "/api/debug/attachment-readiness" `
    -AllowedStatus @(404) `
    -Body @{
        message = "summarize this attached file"
        attachments = @(
            @{
                filename = "debug-disabled.txt"
                summary = "This must not be exposed without NOVA_DEBUG_ROUTES."
    file = Get-Item $tempFile
        }

    Write-Host "Upload ok: $($upload.ok)"
    Write-Host "Upload filename/name: $($upload.filename) / $($upload.name)"
    Write-Host "Upload url/download_url: $($upload.url) / $($upload.download_url)"
    Write-Host "Has attachment summary: $([bool]($upload.attachment_summary -or $upload.extracted_text -or $upload.summary))"

    if ($upload.ok -eq $false) {
        throw "/api/upload returned ok=false"
    }

    if (-not ($upload.filename -or $upload.name)) {
        throw "/api/upload response missing filename/name"
    }

    if (-not ($upload.url -or $upload.download_url -or $upload.path)) {
        throw "/api/upload response missing url/download_url/path"
    }
} finally {
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Attachment API HTTP smoke passed."
