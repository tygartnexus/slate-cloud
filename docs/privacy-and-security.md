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

## Deletion and export

The API implements both, self-service and scoped to the calling account:

- `GET /account/export` streams the account record and every verdict it owns as
  NDJSON, including full stored payloads.
- `DELETE /account?confirm=<account id>` erases the account and its verdicts in
  a single transaction.

Deletion erases the `accounts` row (including `legacy_stripe_customer_id`) and
every verdict payload the account owns. `legacy_licenses_archive` rows are
**retained but stripped**: the signed license token is overwritten, the Stripe
subscription id is nulled, and the account link is dropped, leaving only
non-identifying facts (`license_id`, `tier`, `seats`, dates). This is a
deliberate balance between the erasure this document promises and the audit
retention described in docs/deployment.md.

Two limits an operator must understand and disclose:

- **The Clerk user is not deleted.** Slate Cloud never holds a Clerk secret key,
  so it erases its own data only. Signing in again creates a new empty account.
  If your privacy notice promises identity deletion, you must also delete the
  Clerk user yourself.
- **Backups are not rewritten.** Deletion affects the live database. Purging
  restored copies and snapshots is the operator's responsibility.

Whether this satisfies a given legal obligation is a question for the operator
and their counsel. This document describes what the code does; it is not a
compliance determination.

## Operator responsibilities

Before public or customer use, configure:

- A privacy notice that describes what verdict metadata is stored and why.
- A retention/deletion policy for verdict payloads and accounts.
- Clerk issuer, audience, and authorized-party checks.
- Production Postgres access controls, backups, and migration process.
- TLS, deploy logs, monitoring, and incident response.
- Clerk-side user deletion and backup purging, which the API does not do.

Do not claim production privacy, compliance, or security readiness from this
repository alone. Those claims depend on the operator's deployment, policies,
and legal review.
