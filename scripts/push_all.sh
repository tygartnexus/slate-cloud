#!/usr/bin/env bash
# Push the three Slate repos to GitHub remotes.
#
# Run this yourself after scripts/verify_local_release.ps1 passes.
# Creates each repo public by default for the free/open-source release and
# pushes main in one shot.
#
#   bash scripts/push_all.sh
#
# Override the org or visibility:
#   ORG=your-org VISIBILITY=private bash scripts/push_all.sh
set -euo pipefail

ORG="${ORG:-tygartnexus}"
VISIBILITY="${VISIBILITY:-public}"
if [[ "$VISIBILITY" != "public" && "$VISIBILITY" != "private" ]]; then
  echo "VISIBILITY must be public or private" >&2
  exit 1
fi

push_one() {
  local path="$1" name="$2"
  echo "=== $ORG/$name  (from $path) ==="
  cd "$path"
  if git remote get-url origin >/dev/null 2>&1; then
    echo "  origin already set -> pushing"
    git push -u origin main
  else
    gh repo create "$ORG/$name" "--$VISIBILITY" --source=. --remote=origin --push
  fi
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SLATE_CLOUD_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd -- "$SLATE_CLOUD_ROOT/.." && pwd)"

push_one "$WORKSPACE_ROOT/Slate"      "slate"
push_one "$WORKSPACE_ROOT/SlatePro"   "slate-pro"
push_one "$SLATE_CLOUD_ROOT"          "slate-cloud"

echo
echo "Done. Three $VISIBILITY repos under $ORG:"
echo "  https://github.com/$ORG/slate"
echo "  https://github.com/$ORG/slate-pro"
echo "  https://github.com/$ORG/slate-cloud"
echo
echo "Next: verify public CI, branch protection, and live deployment proof before claiming production readiness."
