"""Account info endpoint tests."""

from __future__ import annotations

from tests.conftest import Ctx


def test_account_info_empty(ctx: Ctx) -> None:
    resp = ctx.client.get("/account")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "test@example.com"
    assert body["verdict_count"] == 0


def test_account_license_endpoint_is_disabled(ctx: Ctx) -> None:
    resp = ctx.client.get("/account/license")
    assert resp.status_code == 410
    assert resp.json()["status"] == "license_not_required"


def test_account_verdict_count_increments(ctx: Ctx) -> None:
    core = {
        "status": "PASS",
        "shot_id": "s1",
        "slate_version": "0.1.0",
        "started_at": "2026-05-20T00:00:00Z",
        "finished_at": "2026-05-20T00:00:01Z",
        "duration_seconds": 1.0,
        "providers_consulted": ["gemma"],
        "frames_analyzed": ["f.png"],
        "failures": [],
        "frame_analyses": [],
        "quality_scores_aggregated": {},
        "response_quality": {
            "mode": "evidence_based",
            "facts": ["The account test uploaded one verdict."],
            "assumptions": ["The test payload represents a completed Slate run."],
            "unknowns": ["No source frames are available in the account test."],
            "confidence_score": 0.8,
            "evidence": ["test payload"],
            "risks": ["A minimal fixture can miss nested verdict edge cases."],
            "counterarguments": ["Endpoint tests cover nested verdicts separately."],
            "recommendation": "Count the uploaded verdict.",
            "tradeoffs": [
                "Strict fixtures are more verbose but exercise the contract."
            ],
            "what_would_change_recommendation": [
                "The upload endpoint rejects the payload."
            ],
        },
    }
    created = ctx.client.post("/verdicts", json={"payload": core})
    assert created.status_code == 201, created.text
    body = ctx.client.get("/account").json()
    assert body["verdict_count"] == 1
