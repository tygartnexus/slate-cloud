# Slate Cloud

The free web dashboard for Slate verdicts. Verdict JSON produced by `slate` is
POSTed to the API, and the dashboard renders verdict history and detail reports —
personas, failures, quality scores, and the `response_quality` evidence blocks.

There is no upload form in the dashboard today: verdicts arrive via
`POST /verdicts` from the CLI or `curl`. See [Not built yet](#not-built-yet).

This repo is MIT-licensed. There is no checkout, billing portal, paid upgrade,
or license activation requirement.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│ Frontend (Next.js 16 + Tailwind, deployed on Vercel) │
│  - Clerk auth (proxy.ts guards /dashboard)           │
│  - Verdict list / detail                             │
│  - Free access status                                │
└──────────────────────────────────────────────────────┘
                          │
                          ▼  REST + Clerk JWT
┌──────────────────────────────────────────────────────┐
│ Backend (FastAPI, deployed on Fly.io / Railway)      │
│  - /verdicts, /account                               │
│  - /health, /ready                                   │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│ Postgres (Neon free tier viable for v1)              │
│  accounts, verdicts                                  │
└──────────────────────────────────────────────────────┘
```

### API surface

| Route | Auth | Notes |
|---|---|---|
| `POST /verdicts` | Clerk JWT | Persist a verdict. `201` on success; see [Upload requirements](#upload-requirements) |
| `GET /verdicts` | Clerk JWT | Caller's verdicts, newest first. `limit` 1–200 (default 50), `offset` ≥ 0 |
| `GET /verdicts/{id}` | Clerk JWT | Detail for one verdict the caller owns; `404` otherwise |
| `GET /account` | Clerk JWT | Account id, email, and true `verdict_count` |
| `GET /health` | none | Liveness only — proves the process is up, nothing more |
| `GET /ready` | none | Readiness. `200` when ready, **`503` when blocked** |
| `POST /billing/checkout`, `POST /billing/portal` | none | `410` — payments disabled |
| `POST /webhooks/stripe` | none | `410` — payments disabled |
| `GET /account/license` | Clerk JWT | `410` — no activation token required |

Slate Cloud stores uploaded **verdict payload JSON** — not frame bytes and not API keys. That payload can still contain shot IDs, model observations, persona reports, manifest-derived fields, and other user-provided metadata that the customer chose to upload. Provider choice controls frame flow: local Ollama keeps sampled frames on the customer's hardware, while NVIDIA or Anthropic lanes send sampled frames to those providers through the customer's own account.

Before hosting Slate Cloud for other users, read
[docs/privacy-and-security.md](docs/privacy-and-security.md). The deployer is
responsible for their own privacy notice, retention policy, Clerk configuration,
database access controls, and incident process.

## Repo layout

```
backend/            FastAPI app, SQLAlchemy models, Alembic migrations
  app/routes/       verdicts, account, readiness, billing + webhook stubs
  app/ai_response_quality.py   the response_quality contract
  migrations/       schema history; autogen.py holds autogenerate exclusions
  tests/            pytest suite (coverage gated at 85%)
frontend/           Next.js 16 app router, Clerk auth, Tailwind
  proxy.ts          route guard (the Next 16 replacement for middleware.ts)
  scripts/verify-content.mjs   public-claim checker
docs/               deployment, privacy/security, response-quality framework
scripts/            verify_local.sh, verify_production_live.ps1
```

## Local dev

### Prereqs

- Python 3.10+ (CI tests 3.10, 3.11, 3.12)
- Node.js 20.9+ (required by Next 16)
- Docker (for the local Postgres)

### Backend

```bash
cp .env.example .env  # set POSTGRES_PASSWORD for local Docker only
docker compose up -d --wait postgres

cd backend
python -m venv .venv
. .venv/Scripts/activate    # Windows
# . .venv/bin/activate      # macOS / Linux
pip install -e ".[dev]"
cp .env.example .env  # set APP_ENV, DATABASE_URL, and CLERK_JWT_PUBLIC_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

SQLite is fine for development and test. It is **blocked in production** — with
`APP_ENV=production` a SQLite `DATABASE_URL` fails the readiness check.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # fill in SLATE_API_URL and CLERK_*
npm run dev   # http://localhost:3000
```

`SLATE_API_URL` is server-only on purpose — authenticated backend calls must not
run from the browser. `frontend/scripts/verify-content.mjs` fails the build if a
browser-exposed (`NEXT_PUBLIC_`-prefixed) API URL variable appears in the scanned
source.

### Quick test (with backend up)

```bash
# Confirm deploy dependencies are configured and reachable.
# 200 when ready, 503 when blocked, so `curl -f` and orchestrator probes
# fail correctly.
curl -f http://localhost:8000/ready

# Upload a verdict
curl -X POST http://localhost:8000/verdicts \
  -H "Authorization: Bearer $CLERK_JWT" \
  -H "Content-Type: application/json" \
  -d @verdict.json
```

### Upload requirements

`POST /verdicts` enforces these limits, each with its own status:

| Condition | Response |
|---|---|
| No `response_quality` object anywhere in the payload | `422` |
| A `response_quality` object that fails the contract | `422` with an `issues` list |
| Nesting deeper than 64 levels | `422` |
| Payload over `VERDICT_MAX_PAYLOAD_BYTES` (512 KB default) | `413` |

The `response_quality` requirement is a hard gate: a verdict without one is
rejected. See
[docs/ai-response-quality-framework.md](docs/ai-response-quality-framework.md)
for the contract, and
[backend/tests/fixtures/current_slate_verdict.json](backend/tests/fixtures/current_slate_verdict.json)
for a payload that satisfies it.

Keys that look like credentials (`api_key`, `access_token`, `authorization`, ...)
become `[redacted]` before the payload is stored. Model-usage metrics such as
`total_tokens` and `token_count` are preserved.

A verdict is marked as having Panel review only when the payload carries a
non-empty `panel` block — not merely a `final_status`.

## Checks

`scripts/verify_local.sh` runs the same gates CI runs (format, lint, types,
migrations, tests, audit, content check, build, e2e):

```bash
bash scripts/verify_local.sh              # everything
SKIP_E2E=1 bash scripts/verify_local.sh   # skip the slow Playwright pass
```

### CI

Two workflows, on push, PR, manual dispatch, and a **weekly schedule** so a new
advisory or tool release surfaces without waiting for a push.

| Job | Covers |
|---|---|
| `pytest` (3.10 / 3.11 / 3.12) | black, ruff, mypy, Alembic smoke, pytest with an 85% coverage gate |
| `postgres` | migrations up → down → up against real Postgres, plus the schema-drift guard |
| `test` | aggregate gate over the two above — the context branch protection requires |
| `typecheck` | npm audit, content check, vitest, eslint, build, tsc, Playwright |

Backend lint/format/type tools are **upper-bounded** in `pyproject.toml`, and the
ruff rule set is selected explicitly. Both are deliberate: unbounded floors plus
inherited defaults meant a tool release could turn CI red with no code change.

`tests/test_schema_drift.py` asserts that `app/models.py` and the Alembic head
describe the same schema. Objects kept for auditability but intentionally
unmapped are excluded in `migrations/autogen.py` — without that,
`alembic revision --autogenerate` proposes dropping them.

## Deploy

See [docs/deployment.md](docs/deployment.md) for the production deploy.

## Access

All Slate Cloud dashboard functionality is free. The legacy `/billing/*`,
`/webhooks/stripe`, and `/account/license` routes return `410` compatibility
responses so stale clients cannot accidentally start a paid flow.

## Not built yet

Stated plainly so the docs do not imply capability that does not exist:

- **No upload UI.** Verdicts reach the API by `POST /verdicts` only.
- **No delete or export endpoints.** [docs/privacy-and-security.md](docs/privacy-and-security.md)
  tells operators to offer account deletion and data export; the API has neither,
  so an operator must service those requests directly against the database.
- **No rate limiting** on any endpoint.
- **No verdict comparison or history diffing.**

## License

MIT — see [LICENSE](LICENSE).
