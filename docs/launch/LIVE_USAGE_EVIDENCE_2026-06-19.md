# Slate live-usage evidence

Date: 2026-06-19
Verdict: public repo and CI gates pass; production live-usage gates remain blocked by missing external infrastructure.

## Passed Gates

### Fresh public repos

| Repo | URL | Public head | Branches |
|---|---|---:|---|
| Slate | https://github.com/tygartnexus/slate | `b86e13e` | `main` only |
| SlatePro | https://github.com/tygartnexus/slate-pro | `43b00dd` | `main` only |
| SlateCloud | https://github.com/tygartnexus/slate-cloud | `0c5b209` | `main` only |

Evidence:

- Fresh public clone check passed for all three repos after the evidence PR merge.
- High-confidence public-clone secret scan passed.
- Each public clone showed only `main`.
- Public heads at final verification:
  - Slate: `b86e13e`
  - SlatePro: `43b00dd`
  - SlateCloud: `0c5b209`

### Public CI

| Repo | Required checks | Result |
|---|---|---|
| Slate | `test (3.10)`, `test (3.11)`, `test (3.12)` | Pass |
| SlatePro | `test (3.10)`, `test (3.11)`, `test (3.12)` | Pass after CI source and coverage fixes |
| SlateCloud | `test`, `typecheck` | Pass |

Evidence:

- Slate CI run `27834359818`: pass.
- SlatePro CI run `27834578279`: pass.
- SlateCloud final backend run `27835056534`: pass.
- SlateCloud final frontend run `27835056519`: pass.

### Branch protection

Branch protection is enabled on `main` for all three repos.

| Repo | Required status checks | Admins enforced | Conversation resolution |
|---|---|---|---|
| Slate | `test (3.10)`, `test (3.11)`, `test (3.12)` | Yes | Yes |
| SlatePro | `test (3.10)`, `test (3.11)`, `test (3.12)` | Yes | Yes |
| SlateCloud | `test`, `typecheck` | Yes | Yes |

### Local release gate

Command:

```powershell
$env:Path = "E:\SlateCloud\.venv\Scripts;$env:Path"
pwsh .\scripts\verify_local_release.ps1
```

Result:

- Secret scan: pass.
- SlateCloud backend: Black, Ruff, mypy, pytest, Alembic smoke all pass.
- SlateCloud frontend: audit, content scan, Vitest, lint, typecheck, build, Playwright all pass.
- Slate: Ruff, mypy, pytest pass.
- SlatePro: Ruff, mypy, pytest pass.

### Local provider runtime

Verified:

- Local Ollama is available.
- `gemma4:latest` is installed.
- `slate verify --provider gemma` completed against generated test frames.
- Resulting verdict status was `FAIL`, which is acceptable for provider proof.
- Verdict included provider `gemma`, three analyzed frames, and valid evidence-based `response_quality`.

Evidence summary:

```json
{
  "status": "FAIL",
  "providers": ["gemma"],
  "frames": ["frame_0000.png", "frame_0001.png", "frame_0002.png"],
  "confidence": 0.68
}
```

## Blocked Gates

### Production deployment

Blocked because these are not configured in the current environment:

- `SLATE_FRONTEND_URL`
- `SLATE_BACKEND_URL`
- `DATABASE_URL`
- production backend host credentials

Required evidence:

- Public frontend URL.
- Public backend URL.
- Production Postgres DB.
- `GET /ready` returning `status: ready`.

### Production Clerk auth

Blocked because these are not configured in the current environment:

- `SLATE_PROD_CLERK_TOKEN`
- `CLERK_SECRET_KEY`
- `CLERK_JWT_PUBLIC_KEY`

Required evidence:

- Real sign-up/sign-in/sign-out proof.
- Protected dashboard blocks unauthenticated users.
- Authenticated API calls work with a real Clerk token.

### Production real-verdict upload

Blocked until production deploy and Clerk token exist.

Required evidence:

- Real provider verdict JSON uploaded through production backend.
- Dashboard list/detail page renders that real verdict.

### Cloud provider lanes

Blocked because these are not configured in the current environment:

- `NVIDIA_API_KEY`
- `ANTHROPIC_API_KEY`

Safe claim:

- Local Ollama/Gemma path has been verified.
- NVIDIA and Anthropic should not be claimed as live verified until real runs complete.

## Current Safe Claim

Slate is public, free, and locally verified with public CI passing. The local
Ollama/Gemma provider path has been tested with real model output. Production
deployment, Clerk auth, production upload, NVIDIA, and Anthropic remain blocked
until the listed external credentials and URLs are available.
