# Slate consolidation gap-closure plan

Updated: 2026-06-18

The paid-option plan is closed. Slate is now positioned as one free/open-source
project with an optional dashboard.

## Current Position

- `slate-ai` contains provider checks, Panel review, and evidence bundles.
- `slate-pro` is deprecated as a compatibility alias, not a separate product.
- Cloud no longer starts checkout, opens billing portals, mints licenses, or
  requires Stripe/issuer secrets.
- Legacy payment and license endpoints return explicit disabled responses.
- Provider costs still belong to the user when they choose cloud model lanes
  such as NVIDIA or Anthropic.

## Remaining Launch Proof

1. Verify the public GitHub repository URL for Slate.
2. Verify clean install from the intended package source for `slate-ai`.
3. Verify deployed Cloud `/ready` with production Clerk and database config.
4. Verify legacy payment endpoints return disabled responses in production.

## Verification Commands

Slate:

```bash
python -m ruff check src tests
python -m mypy src
python -m pytest -q
```

SlatePro compatibility wrapper:

```bash
python -m ruff check src tests
python -m mypy src
python -m pytest -q
```

SlateCloud backend:

```bash
python -m black --check .
python -m ruff check app tests migrations
python -m mypy app
python -m pytest -q
python -m alembic upgrade head
python -m alembic current
```

SlateCloud frontend:

```bash
npm ci
npm audit --audit-level=high
npm run check:content
npm run test
npm run typecheck
npm run lint
npm run build
npm run test:e2e
```
