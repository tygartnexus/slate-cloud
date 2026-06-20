# Slate Cloud privacy and security notes

Slate Cloud is open-source dashboard software, not a hosted service operated by
this repository. If you deploy it for yourself or other users, you are the
operator of that deployment.

## What the dashboard stores

The backend stores:

- Clerk user identifiers and email addresses.
- Uploaded verdict JSON.
- Derived verdict summary fields such as shot id, final status, and submission
  timestamp.

The backend does not need provider API keys and does not store source frame
bytes by design. Uploaded verdict JSON can still contain user-provided metadata,
model observations, filenames, project names, prompts, or accidental sensitive
fields. The API redacts common sensitive-key fields before persistence, but that
is a guardrail, not a privacy program.

## Operator responsibilities

Before public or customer use, configure:

- A privacy notice that describes what verdict metadata is stored and why.
- A retention/deletion policy for verdict payloads and accounts.
- Clerk issuer, audience, and authorized-party checks.
- Production Postgres access controls, backups, and migration process.
- TLS, deploy logs, monitoring, and incident response.
- A support path for account deletion and data export requests.

Do not claim production privacy, compliance, or security readiness from this
repository alone. Those claims depend on the operator's deployment, policies,
and legal review.
