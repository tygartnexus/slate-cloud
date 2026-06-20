# Slate Cloud

The free web dashboard for Slate verdicts. Users upload verdict JSON produced by
`slate`, then view verdict history and detail reports.

This repo is MIT-licensed. There is no checkout, billing portal, paid upgrade,
or license activation requirement.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│ Frontend (Next.js 14 + Tailwind, deployed on Vercel) │
│  - Clerk auth                                        │
│  - Verdict list / detail                             │
│  - Free access status                                │
└──────────────────────────────────────────────────────┘
                          │
                          ▼  REST + Clerk JWT
┌──────────────────────────────────────────────────────┐
│ Backend (FastAPI, deployed on Fly.io / Railway)      │
│  - /verdicts {POST list, GET id}                     │
│  - /accounts                                         │
│  - /ready                                            │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│ Postgres (Neon free tier viable for v1)              │
│  accounts, verdicts                                  │
└──────────────────────────────────────────────────────┘
```

Slate Cloud stores uploaded **verdict payload JSON** — not frame bytes and not API keys. That payload can still contain shot IDs, model observations, persona reports, manifest-derived fields, and other user-provided metadata that the customer chose to upload. Provider choice controls frame flow: local Ollama keeps sampled frames on the customer's hardware, while NVIDIA or Anthropic lanes send sampled frames to those providers through the customer's own account.

Before hosting Slate Cloud for other users, read
[docs/privacy-and-security.md](docs/privacy-and-security.md). The deployer is
responsible for their own privacy notice, retention policy, Clerk configuration,
database access controls, and incident process.

## Local dev

### Prereqs

- Python 3.10+
- Node.js 20+
- Docker (for the local Postgres)

### Backend

```bash
cp .env.example .env  # set POSTGRES_PASSWORD for local Docker only
docker compose up -d postgres

cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev]"
cp .env.example .env  # set APP_ENV, DATABASE_URL, and CLERK_JWT_PUBLIC_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # fill in SLATE_API_URL and CLERK_*
npm run dev   # http://localhost:3000
```

### Quick test (with backend up)

```bash
# Confirm deploy dependencies are configured and reachable
curl http://localhost:8000/ready

# Upload a verdict
curl -X POST http://localhost:8000/verdicts \
  -H "Authorization: Bearer $CLERK_JWT" \
  -H "Content-Type: application/json" \
  -d @verdict.json
```

## Deploy

See [docs/deployment.md](docs/deployment.md) for the production deploy.

## Access

All Slate Cloud dashboard functionality is free. The legacy `/billing/*`,
`/webhooks/stripe`, and `/account/license` routes return disabled compatibility
responses so stale clients cannot accidentally start a paid flow.

## License

MIT — see [LICENSE](LICENSE).
