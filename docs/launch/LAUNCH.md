# Slate launch checklist

Internal launch tracker for the free/open-source Slate project.

## Pre-launch — code + content

- [ ] Publish or verify the public Slate repository URL
- [ ] Publish or verify the public Slate Cloud dashboard repository URL if Cloud is split out
- [ ] Verify `pip install slate-ai` from a clean environment after package release
- [ ] Run the all-black-frame smoke test against the JonsStudio render and confirm Slate fails it
- [ ] Verify `slate verify --panel` end-to-end with a real `ANTHROPIC_API_KEY`
- [ ] Verify `slate verify --panel --panel-provider local` with Ollama
- [ ] Verify `slate bundle --redact-raw-outputs` produces a share-safe tarball
- [ ] Update changelogs with the free/open-source release notes

## Pre-launch — infra

- [ ] Domain: register or confirm `slate.ai`
- [ ] DNS: `slate.ai` -> Vercel; `app.slate.ai` -> Vercel; `api.slate.ai` -> backend host
- [ ] Clerk: create production app, copy the publishable key, server-side secret key, and JWT public key
- [ ] Neon: create production Postgres database, copy connection string
- [ ] Backend host: set `DATABASE_URL` and `CLERK_JWT_PUBLIC_KEY`
- [ ] Vercel: set frontend env vars, including public repo URLs
- [ ] Run `alembic upgrade head` against production DB
- [ ] Verify `https://api.slate.ai/ready` returns `{"status":"ready"}` before launch traffic
- [ ] Verify legacy payment endpoints return disabled responses
- [ ] Smoke test: visit `app.slate.ai`, sign up, POST a verdict with a Clerk JWT, see it appear

## Launch day

- [ ] Publish repositories
- [ ] Post Show HN copy from `LAUNCH_COPY.md`
- [ ] Post ProductHunt copy from `LAUNCH_COPY.md`
- [ ] Post Twitter/X and LinkedIn announcements
- [ ] Reach out to AI cinematic creators with the free/open-source framing
- [ ] Post in relevant UE5 / Blender / AI animation communities

## Post-launch — first 48 hours

- [ ] Monitor comments and issues
- [ ] Watch backend/frontend logs
- [ ] Triage GitHub issues
- [ ] Convert repeated questions into docs updates

## KPIs to watch

| Metric | Target by Day 30 |
|---|---|
| GitHub stars | 1,000+ |
| `pip install slate-ai` downloads | 5,000+ |
| First external issue with a real failure mode | 1 |
| First case study published | 1 |
