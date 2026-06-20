# Slate Cloud — free dashboard deploy

## Hosting picks

| Component | Service | Why |
|---|---|---|
| Frontend | **Vercel** | Free tier viable for v1; Next.js native |
| Backend | **Fly.io** or **Railway** | Python-friendly; cheap; supports persistent volumes |
| Database | **Neon** (Postgres) | Free tier viable; branching for staging |
| Auth | **Clerk** | Lowest dev friction for authenticated dashboards |

Slate Cloud no longer processes payments or mints licenses. Do not configure
Stripe, issuer private keys, checkout links, or activation-token delivery for
this deployment.

## Production env vars (backend)

Set these in Fly/Railway dashboard:

```
APP_ENV                 # production
DATABASE_URL            # Neon/Postgres connection string; SQLite is blocked in production
CLERK_JWT_PUBLIC_KEY    # from Clerk dashboard -> API keys -> JWT public key
CLERK_JWT_ISSUER        # expected issuer for your Clerk app
CLERK_JWT_AUDIENCE      # expected audience for your backend/API
CLERK_JWT_AUTHORIZED_PARTIES # comma-separated frontend client ids/origins you trust
CORS_ALLOWED_ORIGINS    # comma-separated frontend origins allowed to call the API
VERDICT_MAX_PAYLOAD_BYTES # max persisted verdict JSON size
```

After deploying the backend, check:

```bash
curl https://your-backend.example.com/health
curl https://your-backend.example.com/ready
```

`/health` only proves the process is running. `/ready` verifies required env
vars are present, the database URL is safe for the environment, the database
can answer `SELECT 1`, and the expected Alembic revision/schema shape is present.
Treat
`{"status":"blocked"}` as a deploy blocker.

## Production env vars (frontend, Vercel)

```
SLATE_API_URL                       # your backend base URL; server-only
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY   # Clerk publishable key
CLERK_SECRET_KEY                    # Clerk server-side secret key
NEXT_PUBLIC_SLATE_REPO_URL          # verified public Slate repo URL
```

## Database migrations

```bash
cd backend
alembic upgrade head
```

Run on every backend deploy. Add to the Fly/Railway deploy hook.

The free-schema migration keeps legacy commercial data for auditability:
`licenses` is renamed to `legacy_licenses_archive`, and
`accounts.stripe_customer_id` is copied to `accounts.legacy_stripe_customer_id`
before the active payment fields are removed from application models and flows.

## Payment endpoints

The legacy endpoints remain disabled by design:

- `POST /billing/checkout` -> `410 payments_disabled`
- `POST /billing/portal` -> `410 payments_disabled`
- `POST /webhooks/stripe` -> `410 payments_disabled`
- `GET /account/license` -> `410 no license required`
