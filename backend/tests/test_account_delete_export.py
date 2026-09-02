"""Account deletion and export.

Deletion is irreversible, so these tests cover the refusal paths as carefully as
the success path: wrong confirmation, another account's data, and what a second
delete does.
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from app.models import Account, VerdictRecord

RESPONSE_QUALITY = {
    "mode": "evidence_based",
    "facts": ["Sampled frames were reviewed."],
    "assumptions": ["The manifest is accurate."],
    "unknowns": ["Unsampled frames were not reviewed."],
    "confidence_score": 0.5,
    "evidence": ["frame_0001.png"],
    "risks": ["Defects may survive between samples."],
    "counterarguments": ["The artifact may be intentional."],
    "recommendation": "Review before publishing.",
    "tradeoffs": ["Blocking protects quality but slows delivery."],
    "what_would_change_recommendation": ["A full-speed review passes."],
}


def _upload(ctx, shot_id: str = "shot_a") -> str:
    resp = ctx.client.post(
        "/verdicts",
        json={
            "payload": {
                "shot_id": shot_id,
                "final_status": "PASS",
                "response_quality": RESPONSE_QUALITY,
            }
        },
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _ndjson(body: str) -> list[dict]:
    return [json.loads(line) for line in body.splitlines() if line.strip()]


class TestVerdictDelete:
    def test_delete_own_verdict(self, ctx) -> None:
        verdict_id = _upload(ctx)
        assert ctx.client.delete(f"/verdicts/{verdict_id}").status_code == 204
        assert ctx.client.get(f"/verdicts/{verdict_id}").status_code == 404
        assert ctx.client.get("/verdicts").json() == []

    def test_delete_missing_verdict_is_404(self, ctx) -> None:
        assert ctx.client.delete("/verdicts/does-not-exist").status_code == 404

    def test_repeat_delete_is_404(self, ctx) -> None:
        verdict_id = _upload(ctx)
        assert ctx.client.delete(f"/verdicts/{verdict_id}").status_code == 204
        assert ctx.client.delete(f"/verdicts/{verdict_id}").status_code == 404

    def test_cannot_delete_another_accounts_verdict(self, ctx, other_account) -> None:
        """A stranger's verdict is a 404, and it must still be there afterwards."""
        assert (
            ctx.client.delete(f"/verdicts/{other_account.verdict_id}").status_code
            == 404
        )
        with ctx.session() as db:
            assert (
                db.query(VerdictRecord)
                .filter(VerdictRecord.id == other_account.verdict_id)
                .count()
                == 1
            )


class TestExport:
    def test_export_streams_account_and_verdicts(self, ctx) -> None:
        _upload(ctx, "shot_a")
        _upload(ctx, "shot_b")

        resp = ctx.client.get("/account/export")
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("application/x-ndjson")
        assert "attachment" in resp.headers["content-disposition"]

        lines = _ndjson(resp.text)
        header, verdicts = lines[0], lines[1:]
        assert header["type"] == "export_metadata"
        assert header["account"]["id"] == ctx.account_id
        assert header["account"]["email"] == "test@example.com"
        # The header count is what makes a truncated stream detectable.
        assert header["verdict_count"] == 2
        assert len(verdicts) == header["verdict_count"]
        assert {v["shot_id"] for v in verdicts} == {"shot_a", "shot_b"}
        assert verdicts[0]["payload"]["response_quality"]["mode"] == "evidence_based"

    def test_export_with_no_verdicts_is_header_only(self, ctx) -> None:
        lines = _ndjson(ctx.client.get("/account/export").text)
        assert len(lines) == 1
        assert lines[0]["verdict_count"] == 0

    def test_export_excludes_other_accounts(self, ctx, other_account) -> None:
        _upload(ctx, "mine")
        lines = _ndjson(ctx.client.get("/account/export").text)
        shot_ids = {line.get("shot_id") for line in lines if line["type"] == "verdict"}
        assert shot_ids == {"mine"}
        assert lines[0]["verdict_count"] == 1

    def test_export_streams_more_than_one_batch(self, ctx) -> None:
        """Exercise the yield_per path with more rows than the batch size."""
        from app.routes.account import EXPORT_BATCH_SIZE

        total = EXPORT_BATCH_SIZE + 3
        for index in range(total):
            _upload(ctx, f"shot_{index:03d}")
        lines = _ndjson(ctx.client.get("/account/export").text)
        assert lines[0]["verdict_count"] == total
        assert len(lines) - 1 == total


class TestAccountDelete:
    def test_delete_requires_confirmation(self, ctx) -> None:
        assert ctx.client.delete("/account").status_code == 422

    def test_delete_rejects_wrong_confirmation(self, ctx) -> None:
        _upload(ctx)
        resp = ctx.client.delete("/account?confirm=not-my-id")
        assert resp.status_code == 400
        assert "confirm" in resp.json()["detail"]
        # Nothing may have been erased by a refused call.
        assert len(ctx.client.get("/verdicts").json()) == 1

    def test_delete_erases_account_and_verdicts(self, ctx) -> None:
        _upload(ctx, "shot_a")
        _upload(ctx, "shot_b")
        account_id = ctx.account_id

        resp = ctx.client.delete(f"/account?confirm={account_id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "account_deleted"
        assert body["verdicts_deleted"] == 2
        assert body["account_id"] == account_id

        with ctx.session() as db:
            assert db.query(Account).filter(Account.id == account_id).count() == 0
            assert (
                db.query(VerdictRecord)
                .filter(VerdictRecord.account_id == account_id)
                .count()
                == 0
            )

    def test_delete_leaves_other_accounts_untouched(self, ctx, other_account) -> None:
        ctx.client.delete(f"/account?confirm={ctx.account_id}")
        with ctx.session() as db:
            assert (
                db.query(Account).filter(Account.id == other_account.account_id).count()
                == 1
            )
            assert (
                db.query(VerdictRecord)
                .filter(VerdictRecord.account_id == other_account.account_id)
                .count()
                == 1
            )

    def test_delete_anonymises_legacy_archive_without_dropping_the_row(
        self, ctx, legacy_license
    ) -> None:
        """Option B: the row survives, the identifying data does not."""
        resp = ctx.client.delete(f"/account?confirm={ctx.account_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["legacy_licenses_anonymised"] == 1

        with ctx.session() as db:
            row = (
                db.execute(
                    sa.text(
                        "SELECT account_id, token, stripe_subscription_id, license_id, "
                        "tier, seats FROM legacy_licenses_archive WHERE id = :id"
                    ),
                    {"id": legacy_license},
                )
                .mappings()
                .one()
            )

        # Identifying / credential data erased.
        assert row["account_id"] is None
        assert row["token"] == "[erased]"
        assert row["stripe_subscription_id"] is None
        # Non-identifying audit facts retained.
        assert row["license_id"] == "license_legacy"
        assert row["tier"] == "pro"
        assert row["seats"] == 1

    def test_second_delete_is_refused_not_a_crash(self, ctx) -> None:
        """current_account recreates an empty account, so the old id no longer matches."""
        first = ctx.client.delete(f"/account?confirm={ctx.account_id}")
        assert first.status_code == 200
        second = ctx.client.delete(f"/account?confirm={ctx.account_id}")
        assert second.status_code == 400
