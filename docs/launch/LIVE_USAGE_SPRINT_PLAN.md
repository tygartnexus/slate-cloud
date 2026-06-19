# Slate live-usage remediation sprint plan

Date: 2026-06-19
Scope: `E:\SlateCloud`, `E:\Slate`, `E:\SlatePro`
Current verdict: blocked for live production claims until external proof exists

## Sprint Goal

Move Slate from locally verified release candidate to live-usage ready without
turning local, fixture, or documented-only evidence into production claims.

## Definition Of Done

Live usage is done only when all gates below have current evidence.

| Gate | Definition of done | Evidence artifact |
|---|---|---|
| Fresh public repos | Public repos contain only sanitized current history and expected files. | Public GitHub URLs, `git log`, secret scan, clean clone check |
| Public CI | Every required workflow passes on the pushed commit. | GitHub Actions run URLs and commit SHA |
| Production deploy | Frontend and backend are deployed against production config. | Public URLs, deploy logs, `/ready` response |
| Production database | Production Postgres is migrated to head, not SQLite. | Alembic current revision and `/ready` schema check |
| Production auth | Real Clerk sign-up, sign-in, token handoff, and protected dashboard access work. | Browser smoke notes and authenticated API proof |
| Provider runtime | Claimed provider paths emit real verdict JSON with `response_quality`. | Command transcript, redacted config, verdict JSON |
| Cloud upload | A real provider verdict uploads and renders in the dashboard. | Upload response and dashboard detail proof |
| Security/data | No secrets, private keys, local DBs, raw frames, or unintended artifacts are public. | Current-tree and pushed-repo scans |
| Operations | Logs, rollback, backup, and incident paths are known. | Runbook links and smoke evidence |
| Claims | Public copy maps to verified evidence and names missing proof. | Claim audit table and scanner pass |

## Sprint Backlog

### 1. Public repo readiness

Tasks:

- Keep the three fresh Git repos on `main`.
- Stage and commit only sanitized files.
- Push to intended public GitHub repos.
- Confirm no stale histories or paid launch artifacts are present.
- Run current-tree and pushed-repo high-confidence secret scans.

Acceptance criteria:

- Each repo has only clean public commits.
- No live keys, private PEMs, local DBs, raw frame outputs, or generated test artifacts are tracked.
- Public README/docs describe one free Slate product.

Status: locally prepared, external push still required.

### 2. CI enforcement

Tasks:

- Run backend, frontend, Slate, and SlatePro checks in public GitHub Actions.
- Set branch protection to require those workflows.
- Use `npm ci`, dependency audit, content scan, Playwright, Alembic smoke, Python lint/type/test gates.

Acceptance criteria:

- Public CI is green for the exact commit being announced.
- Failed or skipped critical checks block merge.

Status: workflows exist locally; public CI proof still required.

### 3. Production deploy and readiness

Tasks:

- Deploy SlateCloud frontend and backend.
- Configure production Postgres and Clerk env vars.
- Run `alembic upgrade head` against production DB.
- Verify `/ready` returns `status: ready`.
- Confirm production does not use SQLite or test-only E2E bypass env vars.

Acceptance criteria:

- Public frontend and backend URLs are reachable.
- `/ready` passes every required environment, database, and schema check.
- Broken config fails closed.

Status: deployment proof required.

### 4. Production auth

Tasks:

- Configure a real Clerk production application.
- Verify sign-up, sign-in, sign-out, dashboard protection, and API token handoff.
- Verify unauthenticated dashboard/API requests do not expose protected data.
- Verify test-only bypass requires localhost and is absent from production env.

Acceptance criteria:

- Real user auth works end to end.
- Protected data is inaccessible without Clerk auth.
- No fixture-auth path is available in production.

Status: real Clerk proof required.

### 5. Real provider runtime and dashboard upload

Tasks:

- Run the provider paths that public copy claims:
  - local Ollama/Gemma if claimed;
  - NVIDIA only if claimed;
  - Anthropic only if claimed.
- Confirm emitted verdict JSON includes valid `response_quality`.
- Upload a real verdict to SlateCloud using a Clerk token.
- Confirm dashboard list/detail/mode rendering uses the real verdict.

Acceptance criteria:

- At least one real provider output completes end to end.
- Any provider not verified is not claimed as live verified.
- Dashboard proof uses real verdict JSON, not fixtures.

Status: real provider and upload proof required.

### 6. Security, data, and operations

Tasks:

- Run current-tree and public-repo secret scans.
- Confirm ignored artifacts include env files, private keys, local DBs, raw frames, evidence bundles, and generated output.
- Document uploaded data: verdict JSON only unless otherwise configured.
- Configure log access, rollback, DB backup/restore, and incident notes.

Acceptance criteria:

- Public repo and production env expose no secrets.
- Operators can inspect logs and roll back a bad deploy.
- Data handling statements match implemented behavior.

Status: local scans available; production and public scans still required.

### 7. Claim audit

Tasks:

- Run content scanner.
- Review README, docs, launch copy, GitHub description, and LinkedIn copy.
- Remove or qualify unsupported claims.
- Avoid production, benchmark, accuracy, and provider-certification claims until proven.

Acceptance criteria:

- Every public claim maps to evidence.
- Missing production or provider proof is named.
- No fixture/mock evidence is presented as live proof.

Status: scanner exists; final public copy audit required after URLs and CI proof.

## Implemented In This Sprint

- Added `scripts/verify_local_release.ps1` to run local release checks across the three repos.
- Added `scripts/verify_production_live.ps1` to run production smoke checks once URLs and tokens exist.
- Updated push scripts to create public repos by default for the free Slate release.
- Added this plan and `LIVE_USAGE_RUNBOOK.md` for the live proof sequence.

## Remaining External Blockers

- Public GitHub repo URLs do not exist until pushed.
- Public CI cannot be verified until pushed.
- Production URLs do not exist until deployed.
- Real Clerk auth cannot be verified until production Clerk is configured.
- Real provider output cannot be certified until provider credentials and a sample manifest/video are supplied.

