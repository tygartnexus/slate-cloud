param(
  [Parameter(Mandatory = $true)]
  [string]$FrontendUrl,

  [Parameter(Mandatory = $true)]
  [string]$BackendUrl,

  [string]$BearerToken = "",
  [string]$VerdictJsonPath = "",
  [switch]$SkipAuthenticatedChecks,
  [int]$TimeoutSec = 30
)

$ErrorActionPreference = "Stop"

function Normalize-Url($value) {
  return $value.TrimEnd("/")
}

function Step($name) {
  Write-Host ""
  Write-Host "== $name ==" -ForegroundColor Cyan
}

function Invoke-Get($url, $headers = @{}, [switch]$AllowFailure) {
  try {
    return Invoke-WebRequest -Uri $url -Headers $headers -TimeoutSec $TimeoutSec -MaximumRedirection 5
  } catch {
    if ($AllowFailure) {
      return $_.Exception.Response
    }
    throw
  }
}

function Assert-DoesNotContain($text, $needle, $context) {
  if ($text -match [regex]::Escape($needle)) {
    throw "$context unexpectedly contained '$needle'."
  }
}

$frontend = Normalize-Url $FrontendUrl
$backend = Normalize-Url $BackendUrl

Step "frontend public route"
$home = Invoke-Get $frontend
if ($home.StatusCode -lt 200 -or $home.StatusCode -ge 400) {
  throw "Frontend returned HTTP $($home.StatusCode)."
}
if ($home.Content -notmatch "Slate") {
  throw "Frontend response did not contain Slate branding."
}
Write-Host "PASS: frontend responds."

Step "pricing/free route"
$pricing = Invoke-Get "$frontend/pricing"
if ($pricing.StatusCode -lt 200 -or $pricing.StatusCode -ge 400) {
  throw "Pricing route returned HTTP $($pricing.StatusCode)."
}
Assert-DoesNotContain $pricing.Content "Start Pro" "pricing route"
Assert-DoesNotContain $pricing.Content "Stripe Checkout" "pricing route"
Write-Host "PASS: pricing route does not expose paid-tier launch copy."

Step "dashboard unauthenticated protection"
$dashboard = Invoke-Get "$frontend/dashboard" -AllowFailure
$dashboardText = ""
if ($dashboard -and $dashboard.ContentLength -gt 0) {
  try {
    $reader = New-Object System.IO.StreamReader($dashboard.GetResponseStream())
    $dashboardText = $reader.ReadToEnd()
  } catch {
    $dashboardText = ""
  }
}
Assert-DoesNotContain $dashboardText "E2E user" "dashboard unauthenticated response"
Assert-DoesNotContain $dashboardText "1 verdict uploaded" "dashboard unauthenticated response"
Write-Host "PASS: unauthenticated dashboard response did not expose fixture/protected UI."

Step "backend readiness"
$ready = Invoke-RestMethod -Uri "$backend/ready" -TimeoutSec $TimeoutSec
if ($ready.status -ne "ready") {
  $details = ($ready.checks | ConvertTo-Json -Compress)
  throw "Backend readiness is '$($ready.status)': $details"
}
$schemaCheck = $ready.checks | Where-Object { $_.name -eq "database_schema" } | Select-Object -First 1
if (-not $schemaCheck -or $schemaCheck.status -ne "pass") {
  throw "Backend readiness did not include a passing database_schema check."
}
Write-Host "PASS: backend /ready returned ready with schema check."

if ($SkipAuthenticatedChecks) {
  Step "authenticated checks"
  Write-Host "SKIPPED: authenticated upload/list checks were explicitly skipped." -ForegroundColor Yellow
  exit 0
}

if (-not $BearerToken) {
  throw "BearerToken is required unless -SkipAuthenticatedChecks is set."
}

$authHeaders = @{ Authorization = "Bearer $BearerToken" }

Step "authenticated verdict list"
$list = Invoke-RestMethod -Uri "$backend/verdicts" -Headers $authHeaders -TimeoutSec $TimeoutSec
if ($null -eq $list) {
  throw "Authenticated verdict list returned null."
}
Write-Host "PASS: authenticated verdict list succeeded."

if ($VerdictJsonPath) {
  Step "authenticated real verdict upload"
  $resolvedVerdict = Resolve-Path -LiteralPath $VerdictJsonPath -ErrorAction Stop
  $body = Get-Content -Raw -LiteralPath $resolvedVerdict
  $upload = Invoke-RestMethod `
    -Uri "$backend/verdicts" `
    -Method Post `
    -Headers $authHeaders `
    -ContentType "application/json" `
    -Body $body `
    -TimeoutSec $TimeoutSec
  if (-not $upload.id) {
    throw "Verdict upload did not return an id."
  }
  Write-Host "PASS: authenticated verdict upload returned id $($upload.id)."
} else {
  Write-Host "No VerdictJsonPath supplied; upload proof was not checked." -ForegroundColor Yellow
}

Step "production live verdict"
Write-Host "PASS: production smoke checks completed for supplied scope." -ForegroundColor Green
