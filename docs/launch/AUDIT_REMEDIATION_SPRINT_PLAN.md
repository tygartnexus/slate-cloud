# SlateCloud audit remediation sprint plan

Date: 2026-06-18
Scope: `E:\SlateCloud`, current uncommitted worktree on `master...origin/master`
Verdict: Local remediation implemented after adversarial review; production/public release still needs external deployment and current CLI proof

## Evaluation Summary

The initial audit found useful partial work but blocked public release on
migration correctness, false readiness, mode truthfulness, frontend payload
hardening, dependency/audit reproducibility, and E2E evidence.

The local remediation now addresses those code and test gaps. This does not
certify production: real deployment, real Clerk sign-in, current Slate CLI output,
and production `/ready` still need external evidence before launch claims should
say production verified.

## Current Local Verification

- `python -m black --check .`: passed
- `python -m ruff check app tests migrations`: passed
- `python -m mypy app`: passed
- `python -m pytest -q`: passed, 35 tests
- `python -m alembic upgrade head && python -m alembic current`: passed on a temp DB
- `npm ci`: passed, zero vulnerabilities
- `npm audit --audit-level=high`: passed, zero vulnerabilities
- `npm run check:content`: passed, 34 files scanned
- `npm run test`: passed, 5 component tests
- `npm run typecheck`: passed
- `npm run lint`: passed
- `npm run build`: passed
- `npm run test:e2e -- --reporter=line`: passed, 4 Playwright tests
- `PYTHONPATH=E:\Slate\src python -m pytest -q tests/test_response_quality.py tests/test_engine.py tests/test_providers/test_base.py tests/test_panel/test_base_and_prompts.py tests/test_panel/test_verdict.py tests/test_panel/test_fusion.py`: passed, 102 Slate CLI/panel contract tests
- `pwsh .\scripts\verify_local_release.ps1 -SkipSlowChecks -SkipFormatCheck`: passed, with local Black skipped because Windows Application Control blocked the local Black module; CI still runs Black.
- `python -m pytest -q` in `E:\Slate`: passed, 234 tests.
- `python -m pytest -q` in `E:\SlatePro`: passed, 2 tests.

## Initial Audit Evidence

Initial repository state:

- `git status --short --branch`: dirty `master...origin/master`
- `git diff --stat`: 37 tracked files changed, 602 insertions, 1319 deletions
- Untracked release files include `LICENSE`, `backend/app/ai_response_quality.py`,
  `backend/app/routes/readiness.py`, AI quality tests, docs, and frontend scripts.

Backend checks:

- `python -m pytest -q`: passed, 25 tests
- `python -m ruff check app tests`: passed
- `python -m mypy app`: passed
- `python -m black --check .`: initially failed, 9 files would be reformatted
- `python -m alembic current`: initially failed, stale `License` import
- `python -m alembic upgrade head`: initially failed, stale `License` import
- `/ready` smoke with no `DATABASE_URL` and a dummy Clerk public key initially returned
  `{"status":"ready"}` using SQLite fallback

Frontend checks:

- `npm run build`: passed
- `npm run lint`: passed
- `npm run check:content`: passed, but only 6 files scanned
- `npm run typecheck`: passed after `next build`; failed before build while
  `.next/types` files were missing or stale
- `npm audit --audit-level=high`: initially failed because no lockfile existed
- `rg --files | rg "(test|spec|__tests__|vitest|jest|playwright)"`: no frontend
  tests found

External/current-state checks:

- `gh run list --limit 5`: only a dependency-graph run from 2026-05-21 was visible;
  no current CI run exists for the uncommitted changes.
- Secret-pattern scan found no high-confidence secrets.
- Protected dashboard E2E now verifies the auth handoff with an inert Clerk test
  key, a per-run local fixture secret, and a negative wrong-secret case. Real
  Clerk sign-in remains a production/staging proof item.

Adversarial follow-up:

- The E2E auth bypass now requires localhost, fixture env flags, the inert Clerk
  key, the fixture cookie, and a per-run server-side header secret.
- Slate and SlateCloud now both require non-empty response-quality lists and
  substantive text for required sections.

## Release Blockers

| ID | Severity | Area | Finding | Required fix |
|---|---:|---|---|---|
| B1 | P0 | Database | Alembic imports removed `License`; migration commands fail. | Remove stale import and add Alembic smoke to CI. |
| B2 | P0 | Database | `001_initial.py` was rewritten instead of adding a forward migration. | Restore immutable initial migration and add a new migration for free/open-source schema changes. |
| B3 | P0 | Readiness | Missing `DATABASE_URL` can still return `/ready: ready` through SQLite fallback. | Add explicit environment mode and fail readiness for unsafe SQLite outside dev/test. |
| B4 | P0 | Product truth | Dashboard modes are local display filters, not mode-specific AI behavior. | Align frontend/backend modes and persist validated mode provenance or relabel as views. |
| B5 | P0 | Upload compatibility | `/verdicts` now rejects old payloads without proof current CLI always emits `response_quality`. | Add current CLI fixture, schema versioning, and coordinated rejection/deprecation behavior. |
| B6 | P1 | Frontend robustness | Detail UI blindly renders unvalidated payloads and can crash on malformed or legacy verdicts. | Add runtime schema guards and graceful unsupported-shape states. |
| B7 | P1 | Security/reproducibility | No frontend lockfile; `npm audit` cannot run. | Commit lockfile, switch CI to `npm ci`, add audit gate. |
| B8 | P1 | CI | Backend CI misses Alembic, formatter, static checks, and depends on moving `slate-ai` install. | Add required gates and remove or pin external dependency. |
| B9 | P1 | Test coverage | No frontend tests for mode UI, payload fallback, billing removal, or auth/dashboard states. | Add focused component and E2E tests. |
| B10 | P2 | Claims | Content scanner omits changed dashboard/docs surfaces and launch copy contains weak public wording. | Expand scanner and rewrite unsafe/overly self-critical claims. |

## Sprint Goal

Make the current free/open-source SlateCloud release defensible as a local and
CI-verified public repo update without overstating production readiness.

Target outcome:

- Local and CI gates pass from a clean checkout.
- Existing DBs can migrate safely.
- `/ready` fails closed when production configuration is incomplete.
- AI response modes are either truly mode-specific or honestly labeled as views.
- Frontend renders malformed/legacy verdict payloads safely.
- Public claims are bounded to verified evidence.

## Sprint Plan

### Sprint 1: Release integrity and fail-closed readiness

Duration: 3-4 engineering days
Owner profile: backend/API plus release engineer

Tasks:

1. Restore `backend/migrations/versions/001_initial.py` to the committed schema.
2. Add a new Alembic revision for the free/open-source schema:
   - add `verdicts.has_panel_review`
   - backfill from `verdicts.is_pro`
   - preserve or intentionally drop old license/payment tables after a backup note
   - remove `accounts.stripe_customer_id` only through a forward migration
3. Fix `backend/migrations/env.py` to import only existing models.
4. Add migration tests:
   - upgrade from old `001_initial`
   - verify `has_panel_review` backfill
   - verify current metadata matches migrated DB
5. Add explicit `APP_ENV` or equivalent deployment mode.
6. Make `DATABASE_URL` required outside dev/test.
7. Update `/ready` to fail on missing DB config or unsafe SQLite in production.
8. Add readiness tests for missing DB URL, SQLite in production, and passing dev mode.
9. Run Black or adopt Ruff formatting consistently.

Acceptance criteria:

- `python -m alembic current` passes.
- `python -m alembic upgrade head` passes on a temp DB.
- Old-schema migration test passes.
- `/ready` returns blocked when `DATABASE_URL` is missing in production mode.
- `python -m black --check .`, `ruff`, `mypy`, and `pytest` all pass.

### Sprint 2: Honest response modes and upload compatibility

Duration: 3-5 engineering days
Owner profile: backend/API plus product engineer

Tasks:

1. Decide the mode model:
   - Option A: one `response_quality` object with a validated `mode` field
   - Option B: per-mode response-quality blocks keyed by mode
2. Align enum names between backend and frontend.
3. Persist mode provenance in uploaded verdict payloads or metadata.
4. Validate mode-specific requirements:
   - red-team mode must include explicit risks and counterarguments
   - legal mode must include non-advice caveat and jurisdiction/source limits
   - technical mode must include runtime/test/evidence notes
   - executive mode must include decision tradeoffs and change criteria
5. Add a current Slate CLI output fixture proving `response_quality` is emitted.
6. Add upload schema versioning.
7. For old clients, choose and implement one policy:
   - hard reject with a clear upgrade error and version docs
   - temporary compatibility wrapper that marks evidence missing
8. Update docs so dashboard modes do not imply AI work that was not performed.

Acceptance criteria:

- Backend tests prove mode validation behavior.
- Frontend labels match persisted mode provenance.
- A real current CLI fixture uploads successfully.
- A legacy fixture fails with a precise, documented response or is safely wrapped.

### Sprint 3: Frontend hardening and test coverage

Duration: 3-4 engineering days
Owner profile: frontend engineer

Tasks:

1. Add runtime validation for API responses before rendering.
2. Add safe fallback states for unsupported verdict shapes.
3. Display persona-level `response_quality` instead of incorrectly saying it is absent.
4. Harden score rendering so non-numeric values cannot crash `toFixed`.
5. Harden `panel.per_persona` and `flags` rendering for missing arrays.
6. Add frontend unit/component tests for:
   - mode selector labels and provenance
   - missing response-quality state
   - persona-level response-quality fallback
   - malformed scores/personas/flags
   - `has_panel_review` display
   - removed checkout/upgrade UI
7. Add Playwright E2E scaffold:
   - public home page
   - pricing/free-access page
   - protected dashboard redirect/sign-in state
   - authenticated dashboard with a test Clerk/session fixture or mocked auth in a test-only route

Acceptance criteria:

- `npm test` exists and passes.
- `npx playwright test` exists for public and protected route smoke.
- Malformed verdict payloads render a clear unsupported-state message, not a crash.

### Sprint 4: CI, dependency, and claim gates

Duration: 2-3 engineering days
Owner profile: release engineer plus product reviewer

Tasks:

1. Generate and commit `frontend/package-lock.json`.
2. Replace frontend CI `npm install` with `npm ci`.
3. Add `npm audit --audit-level=high` to CI.
4. Remove or pin the backend workflow's `slate-ai` install step.
5. Add backend CI gates:
   - `python -m black --check .`
   - `python -m ruff check app tests`
   - `python -m mypy app`
   - `python -m alembic current`
   - temp DB migration upgrade smoke
6. Expand content scanner beyond six files:
   - all `README.md`
   - all docs
   - frontend app/routes/components
   - backend public response strings
7. Rewrite launch copy:
   - replace self-dismissive maturity wording with evidence-based maturity wording
   - avoid absolute coverage wording unless every frame and shot is actually inspected
   - keep free/open-source claims tied to committed `LICENSE` and disabled endpoint tests
8. Add a public-release checklist entry requiring fresh CI run URLs.

Acceptance criteria:

- CI is reproducible from lockfiles and pinned dependencies.
- Content scanner covers all changed public surfaces.
- Public claims are classified as tested locally, built locally, verified staging,
  verified production, or blocked.
- Fresh workflow runs exist for backend and frontend.

## Definition of Done

The remediation sprint is complete only when all of the following are true:

- Clean checkout install works for backend and frontend.
- Backend tests, frontend tests, lint, type checks, build, audit, and migrations pass.
- Alembic upgrade is tested from the previous production schema.
- `/ready` fails closed for missing production configuration.
- Dashboard mode UI cannot imply unperformed AI review.
- Current CLI output uploads successfully, and legacy behavior is documented.
- Protected dashboard E2E is verified with a real or controlled test auth path.
- Secret scan and claim scan pass.
- The final release summary names test commands, CI URLs, remaining risks, and
  any production/staging evidence gaps.

## Recommended Execution Order

1. Fix Alembic and readiness first; do not spend time polishing UI while deploy
   safety is broken.
2. Fix mode provenance before adding more mode UI.
3. Add frontend validation before broad E2E, so tests assert the desired failure
   states instead of snapshotting crashes.
4. Add lockfile/CI gates before final release review.
5. Run a second adversarial review after Sprint 4 and before publishing.
