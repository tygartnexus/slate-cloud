#!/usr/bin/env bash
# Run the same gates CI runs, against this repo only.
#
#   bash scripts/verify_local.sh
#   SKIP_E2E=1 bash scripts/verify_local.sh   # skip the slow Playwright pass
#
# Replaces the previous verify_local_release.ps1, which assumed sibling
# `../Slate` and `../SlatePro` checkouts and aborted for anyone else.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

: "${APP_ENV:=test}"
: "${DATABASE_URL:=sqlite:///./verify_local.db}"
: "${CLERK_JWT_PUBLIC_KEY:=test-clerk-public-key}"
export APP_ENV DATABASE_URL CLERK_JWT_PUBLIC_KEY

step() { printf '\n\033[36m== %s ==\033[0m\n' "$1"; }

step "backend: format"
(cd "$ROOT/backend" && python -m black --check .)

step "backend: lint"
(cd "$ROOT/backend" && python -m ruff check app tests migrations)

step "backend: types"
(cd "$ROOT/backend" && python -m mypy app)

step "backend: migrations"
(cd "$ROOT/backend" && python -m alembic upgrade head && python -m alembic current)

step "backend: tests (coverage gate in pyproject)"
(cd "$ROOT/backend" && python -m pytest -q)

step "frontend: dependency audit"
(cd "$ROOT/frontend" && npm audit --audit-level=high)

step "frontend: content claim check"
(cd "$ROOT/frontend" && npm run check:content)

step "frontend: unit tests"
(cd "$ROOT/frontend" && npm run test)

step "frontend: lint"
(cd "$ROOT/frontend" && npm run lint)

step "frontend: build"
(cd "$ROOT/frontend" && npm run build)

step "frontend: types"
(cd "$ROOT/frontend" && npm run typecheck)

if [[ "${SKIP_E2E:-0}" != "1" ]]; then
  step "frontend: end-to-end"
  (cd "$ROOT/frontend" && npm run test:e2e -- --reporter=line)
fi

printf '\n\033[32mPASS: local gates completed.\033[0m\n'
printf 'This proves local readiness only. Production still needs its own evidence.\n'
