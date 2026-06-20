param(
  [string]$SlateCloudRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path,
  [string]$SlateRoot = (Join-Path (Split-Path -Parent (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path) "Slate"),
  [string]$SlateProRoot = (Join-Path (Split-Path -Parent (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path) "SlatePro"),
  [switch]$SkipSlowChecks,
  [switch]$SkipFormatCheck
)

$ErrorActionPreference = "Stop"

$secretPattern = "(sk_live_[A-Za-z0-9_\-]+|rk_live_[A-Za-z0-9_\-]+|pk_live_[A-Za-z0-9_\-]+|xox[baprs]-[A-Za-z0-9\-]+|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|AIza[0-9A-Za-z_\-]{35}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)"

function Step($name) {
  Write-Host ""
  Write-Host "== $name ==" -ForegroundColor Cyan
}

function Invoke-Checked($workingDirectory, $command, $environment = @{}, $Shell = "cmd") {
  Step "$workingDirectory :: $command"
  Push-Location -LiteralPath $workingDirectory
  $previousValues = @{}
  try {
    foreach ($key in $environment.Keys) {
      $previousValues[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
      [Environment]::SetEnvironmentVariable($key, [string]$environment[$key], "Process")
    }
    if ($Shell -eq "powershell") {
      powershell -NoProfile -ExecutionPolicy Bypass -Command $command
    } else {
      cmd /d /c $command
    }
    if ($LASTEXITCODE -ne 0) {
      throw "Command failed with exit code $LASTEXITCODE"
    }
  } finally {
    foreach ($key in $environment.Keys) {
      [Environment]::SetEnvironmentVariable($key, $previousValues[$key], "Process")
    }
    Pop-Location
  }
}

function Assert-Repo($path) {
  $resolved = Resolve-Path -LiteralPath $path -ErrorAction Stop
  if (-not (Test-Path -LiteralPath (Join-Path $resolved ".git"))) {
    throw "Missing .git directory at $resolved"
  }
  return $resolved.Path
}

function Invoke-SecretScan($paths) {
  Step "high-confidence current-tree secret scan"
  $scanArgs = @(
    "-n",
    "-uu",
    "--hidden",
    "--glob", "!**/.git/**",
    "--glob", "!**/node_modules/**",
    "--glob", "!**/.venv/**",
    "--glob", "!**/venv/**",
    "--glob", "!**/.next/**",
    "--glob", "!**/.pytest_cache/**",
    "--glob", "!**/__pycache__/**",
    "--glob", "!**/.mypy_cache/**",
    "--glob", "!**/.ruff_cache/**",
    "--glob", "!**/dist/**",
    "--glob", "!**/build/**",
    "-l",
    $secretPattern
  ) + $paths

  & rg @scanArgs
  $exit = $LASTEXITCODE
  if ($exit -eq 0) {
    throw "Secret scan found high-confidence matches."
  }
  if ($exit -gt 1) {
    throw "Secret scan failed with exit code $exit."
  }
  Write-Host "No high-confidence secret matches found."
}

$slateCloud = Assert-Repo $SlateCloudRoot
$slate = Assert-Repo $SlateRoot
$slatePro = Assert-Repo $SlateProRoot

Invoke-SecretScan @($slateCloud, $slate, $slatePro)

if ($SkipFormatCheck) {
  Step "$slateCloud\backend :: python -m black --check ."
  Write-Host "SKIPPED: local Python/Black is blocked on this workstation. CI must run this gate." -ForegroundColor Yellow
} else {
  Invoke-Checked (Join-Path $slateCloud "backend") "python -m black --check ."
}
Invoke-Checked (Join-Path $slateCloud "backend") "python -m ruff check app tests migrations"
Invoke-Checked (Join-Path $slateCloud "backend") "python -m mypy app" @{
  APP_ENV = "test"
  DATABASE_URL = "sqlite:///./typecheck.db"
  CLERK_JWT_PUBLIC_KEY = "test-public-key"
}
Invoke-Checked (Join-Path $slateCloud "backend") "python -m pytest -q" @{
  APP_ENV = "test"
  DATABASE_URL = "sqlite:///./pytest.db"
  CLERK_JWT_PUBLIC_KEY = "test-public-key"
}
Invoke-Checked (Join-Path $slateCloud "backend") "`$db = Join-Path (Get-Location) 'alembic-check.db'; Remove-Item -LiteralPath `$db -Force -ErrorAction SilentlyContinue; python -m alembic upgrade head; `$upgradeExit = `$LASTEXITCODE; python -m alembic current; `$currentExit = `$LASTEXITCODE; Remove-Item -LiteralPath `$db -Force -ErrorAction SilentlyContinue; if (`$upgradeExit -ne 0 -or `$currentExit -ne 0) { exit 1 }" @{
  APP_ENV = "test"
  DATABASE_URL = "sqlite:///./alembic-check.db"
  CLERK_JWT_PUBLIC_KEY = "test-public-key"
} "powershell"

Invoke-Checked (Join-Path $slateCloud "frontend") "npm audit --audit-level=high"
Invoke-Checked (Join-Path $slateCloud "frontend") "npm run check:content"
Invoke-Checked (Join-Path $slateCloud "frontend") "npm run test"
Invoke-Checked (Join-Path $slateCloud "frontend") "npm run lint"
Invoke-Checked (Join-Path $slateCloud "frontend") "npm run typecheck"
Invoke-Checked (Join-Path $slateCloud "frontend") "npm run build"
if (-not $SkipSlowChecks) {
  Invoke-Checked (Join-Path $slateCloud "frontend") "npm run test:e2e -- --reporter=line"
}

Invoke-Checked $slate "python -m ruff check src tests"
Invoke-Checked $slate "python -m mypy src"
Invoke-Checked $slate "python -m pytest -q" @{
  PYTHONPATH = (Join-Path $slate "src")
}

Invoke-Checked $slatePro "python -m ruff check src tests"
Invoke-Checked $slatePro "python -m mypy src"
Invoke-Checked $slatePro "python -m pytest -q"

Step "local release verdict"
Write-Host "PASS: local release checks completed. This proves local readiness only; production and public CI still require separate evidence." -ForegroundColor Green
