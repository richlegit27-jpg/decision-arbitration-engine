param(
    [string]$BaseUrl = "https://decision-arbitration-engine-production.up.railway.app"
)

$ErrorActionPreference = "Stop"

$BaseUrl = $BaseUrl.TrimEnd("/")

Write-Host ""
Write-Host "NOVA RAILWAY RELEASE CHECK"
Write-Host "BaseUrl: $BaseUrl"
Write-Host ""

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}


# NOVA_RAILWAY_RESPONSE_TEXT_DECODER_20260709
function Get-ResponseText {
    param(
        [Parameter(Mandatory = $true)]
        $Response
    )

    $content = $Response.Content

    if ($null -eq $content) {
        return ""
    }

    if ($content -is [byte[]]) {
        return [System.Text.Encoding]::UTF8.GetString($content)
    }

    if ($content -is [System.Array]) {
        try {
            $bytes = [byte[]]$content
            return [System.Text.Encoding]::UTF8.GetString($bytes)
        } catch {
            return ($content -join "")
        }
    }

    return [string]$content
}
# /NOVA_RAILWAY_RESPONSE_TEXT_DECODER_20260709

function Get-Text {
    param(
        [string]$Path,
        [Microsoft.PowerShell.Commands.WebRequestSession]$Session = $null
    )

    $uri = "$BaseUrl$Path"

    if ($Session) {
        return Invoke-WebRequest -Uri $uri -WebSession $Session -UseBasicParsing
    }

    return Invoke-WebRequest -Uri $uri -UseBasicParsing
}

Write-Host "Checking public pages..."

$publicChecks = @(
    @{ Path = "/nova-home-preview"; Contains = "Nova" },
    @{ Path = "/contact"; Contains = "Contact" },
    @{ Path = "/privacy"; Contains = "Privacy" },
    @{ Path = "/terms"; Contains = "Terms" },
    @{ Path = "/billing"; Contains = "Billing" },
    @{ Path = "/blog"; Contains = "Blog" },
    @{ Path = "/faq"; Contains = "FAQ" },
    @{ Path = "/roadmap"; Contains = "Roadmap" }
)

foreach ($check in $publicChecks) {
    $response = Get-Text -Path $check.Path
    $body = Get-ResponseText -Response $response

    Write-Host "$($check.Path) -> $($response.StatusCode) | $($response.Headers["Content-Type"])"

    Assert-True ($response.StatusCode -eq 200) "$($check.Path) did not return 200"
    Assert-True ($body -match [regex]::Escape($check.Contains)) "$($check.Path) missing expected text: $($check.Contains)"
}

Write-Host ""
Write-Host "Checking static/SEO assets..."

$assetChecks = @(
    @{ Path = "/sitemap.xml"; Contains = "urlset" },
    @{ Path = "/robots.txt"; Contains = "User-agent" },
    @{ Path = "/static/favicon.svg"; Contains = "<svg" },
    @{ Path = "/static/site.webmanifest"; Contains = "name" },
    @{ Path = "/static/nova-og.svg"; Contains = "<svg" }
)

foreach ($check in $assetChecks) {
    $response = Get-Text -Path $check.Path
    $body = Get-ResponseText -Response $response

    Write-Host "$($check.Path) -> $($response.StatusCode) | $($response.Headers["Content-Type"])"

    Assert-True ($response.StatusCode -eq 200) "$($check.Path) did not return 200"
    Assert-True ($body -match [regex]::Escape($check.Contains)) "$($check.Path) missing expected text: $($check.Contains)"
}

Write-Host ""
Write-Host "Checking owner/admin pages..."

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

$loginResponse = Invoke-WebRequest -Uri "$BaseUrl/richard-login" -WebSession $session -UseBasicParsing -MaximumRedirection 5
Write-Host "/richard-login -> $($loginResponse.StatusCode) | $($loginResponse.BaseResponse.ResponseUri)"

$admin = Get-Text -Path "/admin" -Session $session
$adminBody = Get-ResponseText -Response $admin
Write-Host "/admin -> $($admin.StatusCode) | $($admin.Headers["Content-Type"]) | $($adminBody.Length)"

Assert-True ($admin.StatusCode -eq 200) "/admin did not return 200 after owner login"
Assert-True ($adminBody -match "Nova Admin") "/admin missing Nova Admin"
Assert-True ($adminBody -match "/admin/leads") "/admin missing leads link"

$leads = Get-Text -Path "/admin/leads" -Session $session
$leadsBody = Get-ResponseText -Response $leads
Write-Host "/admin/leads -> $($leads.StatusCode) | $($leads.Headers["Content-Type"]) | $($leadsBody.Length)"

Assert-True ($leads.StatusCode -eq 200) "/admin/leads did not return 200 after owner login"
Assert-True ($leadsBody -match "Nova Leads") "/admin/leads missing Nova Leads"
Assert-True ($leadsBody -match "Export CSV") "/admin/leads missing Export CSV"
Assert-True ($leadsBody -match "Lead filters") "/admin/leads missing Lead filters"

$csv = Get-Text -Path "/admin/leads.csv?q=Richard&kind=contact&limit=100" -Session $session
$csvBody = Get-ResponseText -Response $csv
$csvDisposition = [string]$csv.Headers["Content-Disposition"]
Write-Host "/admin/leads.csv filtered -> $($csv.StatusCode) | $($csv.Headers["Content-Type"]) | $csvDisposition"

Assert-True ($csv.StatusCode -eq 200) "/admin/leads.csv did not return 200"
Assert-True ($csvBody -match "created_at,kind,name,email,interest,message,source") "/admin/leads.csv missing CSV header"
Assert-True ($csvDisposition -match "attachment") "/admin/leads.csv missing attachment disposition"

Write-Host ""

Write-Host ""
Write-Host "Checking owner-only admin pills..."

$ownerHome = Get-Text -Path "/nova-home-preview" -Session $session
$ownerHomeBody = Get-ResponseText -Response $ownerHome
Write-Host "/nova-home-preview owner admin pill -> $($ownerHome.StatusCode) | $($ownerHomeBody.Length)"

Assert-True ($ownerHome.StatusCode -eq 200) "/nova-home-preview owner did not return 200"
Assert-True ($ownerHomeBody -match "Open Nova admin dashboard") "/nova-home-preview missing owner admin pill after login"
Assert-True ($ownerHomeBody -match 'href="/admin"') "/nova-home-preview owner admin pill missing /admin href"

$ownerContact = Get-Text -Path "/contact" -Session $session
$ownerContactBody = Get-ResponseText -Response $ownerContact
Write-Host "/contact owner admin pill -> $($ownerContact.StatusCode) | $($ownerContactBody.Length)"

Assert-True ($ownerContact.StatusCode -eq 200) "/contact owner did not return 200"
Assert-True ($ownerContactBody -match "Open Nova admin dashboard") "/contact missing owner admin pill after login"
Assert-True ($ownerContactBody -match 'href="/admin"') "/contact owner admin pill missing /admin href"

$publicContact = Get-Text -Path "/contact"
$publicContactBody = Get-ResponseText -Response $publicContact
Write-Host "/contact public admin pill hidden -> $($publicContact.StatusCode) | $($publicContactBody.Length)"

Assert-True ($publicContact.StatusCode -eq 200) "/contact public did not return 200"
Assert-True (-not ($publicContactBody -match "Open Nova admin dashboard")) "/contact leaked owner admin pill to public visitor"
# NOVA_RAILWAY_RELEASE_CHECK_OWNER_PILLS_20260709

Write-Host "NOVA RAILWAY RELEASE CHECK PASSED"


