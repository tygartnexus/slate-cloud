# Push the three Slate repos to GitHub remotes.
#
# Run this yourself after `scripts\verify_local_release.ps1` passes.
# Creates each repo public by default for the free/open-source release and
# pushes main.
#
#   pwsh scripts\push_all.ps1
#
# Override the org or visibility:
#   $env:ORG = "your-org"; $env:VISIBILITY = "private"; pwsh scripts\push_all.ps1

$ErrorActionPreference = "Stop"
$org = if ($env:ORG) { $env:ORG } else { "tygartnexus" }
$visibility = if ($env:VISIBILITY) { $env:VISIBILITY } else { "public" }
if ($visibility -notin @("public", "private")) {
  throw "VISIBILITY must be 'public' or 'private'."
}

function Push-One($path, $name) {
  Write-Host "=== $org/$name  (from $path) ==="
  Set-Location $path
  $hasOrigin = $false
  try { git remote get-url origin *> $null; $hasOrigin = $true } catch { $hasOrigin = $false }
  if ($hasOrigin) {
    Write-Host "  origin already set -> pushing"
    git push -u origin main
  } else {
    $visibilityFlag = if ($visibility -eq "public") { "--public" } else { "--private" }
    gh repo create "$org/$name" $visibilityFlag --source=. --remote=origin --push
  }
}

Push-One "E:\Slate"      "slate"
Push-One "E:\SlatePro"   "slate-pro"
Push-One "E:\SlateCloud" "slate-cloud"

Write-Host ""
Write-Host "Done. Three $visibility repos under $org."
Write-Host "Next: verify public CI, branch protection, and live deployment proof before claiming production readiness."
