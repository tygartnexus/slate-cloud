# Slate live-usage runbook

Use this runbook when preparing Slate for real users. Do not mark a step
complete from local evidence when the step requires public or production proof.

## 1. Verify local release candidate

From `E:\SlateCloud`:

```powershell
pwsh .\scripts\verify_local_release.ps1
```

Expected result:

- SlateCloud backend checks pass.
- SlateCloud frontend checks pass.
- Slate CLI/panel tests pass.
- SlatePro compatibility tests pass.
- Current-tree high-confidence secret scan has no matches.

If this fails, fix code before publishing.

## 2. Create clean public repos

From `E:\SlateCloud`:

```powershell
git add .
git commit -m "Initial public Slate Cloud release"

Set-Location E:\Slate
git add .
git commit -m "Initial public Slate release"

Set-Location E:\SlatePro
git add .
git commit -m "Initial public SlatePro compatibility release"
```

Then push:

```powershell
Set-Location E:\SlateCloud
pwsh .\scripts\push_all.ps1
```

Evidence to save:

- GitHub repo URLs.
- Commit SHAs.
- `git log --oneline --all` from each repo.
- Secret scan output against each public clone.

## 3. Verify public CI

For each public repo:

```powershell
gh run list --limit 5
gh run view --log
```

Evidence to save:

- Workflow run URLs.
- Commit SHA matched to the initial release commit.
- Any skipped or failed check explanation.

Pass criteria:

- Required workflows are green.
- Branch protection requires those workflows on `main`.

## 4. Deploy production

Backend requirements:

- `APP_ENV=production`
- `DATABASE_URL` points to production Postgres
- `CLERK_JWT_PUBLIC_KEY` from the Clerk production app
- No SQLite
- No `SLATE_E2E_AUTH_BYPASS`
- No `NEXT_PUBLIC_SLATE_E2E_AUTH_BYPASS`
- No `SLATE_E2E_API_FIXTURE`
- No `SLATE_E2E_AUTH_SECRET`

Frontend requirements:

- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` from the Clerk production app
- `CLERK_SECRET_KEY` stored as a server-side secret
- `SLATE_API_URL` points to the backend production URL
- Public repo URL env vars point to the public repos

Run production migration:

```powershell
alembic upgrade head
alembic current
```

## 5. Run production smoke checks

From `E:\SlateCloud`:

```powershell
pwsh .\scripts\verify_production_live.ps1 `
  -FrontendUrl "https://app.example.com" `
  -BackendUrl "https://api.example.com"
```

For authenticated API proof, add a real Clerk bearer token and a real verdict:

```powershell
pwsh .\scripts\verify_production_live.ps1 `
  -FrontendUrl "https://app.example.com" `
  -BackendUrl "https://api.example.com" `
  -BearerToken $env:SLATE_PROD_CLERK_TOKEN `
  -VerdictJsonPath "C:\path\to\real-verdict.json"
```

Pass criteria:

- Frontend responds.
- Pricing/free-access route responds.
- Dashboard does not expose protected UI without auth.
- Backend `/ready` returns `status: ready`.
- Optional authenticated upload succeeds with real verdict JSON.

## 6. Verify real provider output

Run only the providers you intend to claim. Examples:

```powershell
Set-Location E:\Slate
slate verify examples\basic\manifest.json --provider gemma --output .\artifacts\gemma-verdict.json
slate verify examples\basic\manifest.json --provider nvidia --output .\artifacts\nvidia-verdict.json
slate verify examples\basic\manifest.json --panel --output .\artifacts\panel-verdict.json
```

Evidence to save:

- Command transcript.
- Redacted provider configuration.
- Generated verdict JSON.
- Confirmation that `response_quality` validates.
- Dashboard upload proof.

If a provider path is not verified, do not claim it as live verified.

## 7. Final claim audit

Run:

```powershell
Set-Location E:\SlateCloud\frontend
npm run check:content
```

Manual checks:

- README and docs do not claim production proof unless production URLs were checked.
- No accuracy percentage is published without benchmark artifacts.
- No provider is claimed live verified without a real provider run.
- Fixture-backed screenshots or tests are labeled as fixture/local evidence.

Safe final wording:

> Slate is free and open source. The current public repos and local tests verify
> the release artifacts. Production deployment, auth, and provider paths were
> verified on [date] for the specific URLs and providers listed in the launch
> evidence.

