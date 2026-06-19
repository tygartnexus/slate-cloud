"""Verdict upload / list / detail endpoint tests."""

from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import Ctx

FIXTURES = Path(__file__).parent / "fixtures"

CORE_VERDICT = {
    "status": "PASS",
    "shot_id": "village_walk_001",
    "slate_version": "0.1.0",
    "started_at": "2026-05-20T00:00:00Z",
    "finished_at": "2026-05-20T00:00:05Z",
    "duration_seconds": 5.0,
    "providers_consulted": ["gemma"],
    "frames_analyzed": ["frame_0000.png"],
    "failures": [],
    "frame_analyses": [],
    "quality_scores_aggregated": {"lighting_quality": 4.0},
    "response_quality": {
        "mode": "evidence_based",
        "facts": ["Core analyzed one frame."],
        "assumptions": ["Manifest is accurate."],
        "unknowns": ["Unsampled frames were not inspected."],
        "confidence_score": 0.78,
        "evidence": ["frame_0000.png"],
        "risks": ["Provider may miss visual issues."],
        "counterarguments": ["The sampled frame may be representative."],
        "recommendation": "Continue review.",
        "tradeoffs": ["More frames increase runtime."],
        "what_would_change_recommendation": ["A later frame with a blocker."],
    },
}

ENHANCED_VERDICT = {
    "final_status": "PANEL_BLOCKED",
    "core": CORE_VERDICT,
    "panel": {
        "publish_ready": False,
        "per_persona": [],
        "fused_critical_flags": [],
        "fused_high_flags": [],
        "summary": "animator blocks",
        "response_quality": CORE_VERDICT["response_quality"],
    },
    "response_quality": CORE_VERDICT["response_quality"],
}


def test_upload_core_verdict(ctx: Ctx) -> None:
    resp = ctx.client.post("/verdicts", json={"payload": CORE_VERDICT})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["shot_id"] == "village_walk_001"
    assert body["final_status"] == "PASS"
    assert body["has_panel_review"] is False


def test_upload_current_slate_cli_fixture(ctx: Ctx) -> None:
    payload = json.loads((FIXTURES / "current_slate_verdict.json").read_text("utf-8"))

    resp = ctx.client.post("/verdicts", json={"payload": payload})

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["shot_id"] == "village_walk_001"
    assert body["final_status"] == "FAIL"
    assert body["payload"]["response_quality"]["mode"] == "evidence_based"


def test_upload_rejects_verdict_without_response_quality(ctx: Ctx) -> None:
    payload = dict(CORE_VERDICT)
    payload.pop("response_quality")

    resp = ctx.client.post("/verdicts", json={"payload": payload})

    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["message"] == "verdict response_quality contract failed"
    assert "at least one response_quality" in body["detail"]["issues"][0]


def test_upload_rejects_legacy_response_quality_without_mode(ctx: Ctx) -> None:
    payload = {
        **CORE_VERDICT,
        "response_quality": {
            key: value
            for key, value in CORE_VERDICT["response_quality"].items()
            if key != "mode"
        },
    }

    resp = ctx.client.post("/verdicts", json={"payload": payload})

    assert resp.status_code == 422
    assert "upgrade Slate CLI" in resp.text


def test_upload_rejects_incomplete_response_quality(ctx: Ctx) -> None:
    payload = dict(CORE_VERDICT)
    payload["response_quality"] = {
        **CORE_VERDICT["response_quality"],
        "tradeoffs": [],
    }

    resp = ctx.client.post("/verdicts", json={"payload": payload})

    assert resp.status_code == 422
    assert "tradeoffs" in resp.text


def test_upload_enhanced_verdict_marks_panel_review(ctx: Ctx) -> None:
    resp = ctx.client.post("/verdicts", json={"payload": ENHANCED_VERDICT})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["final_status"] == "PANEL_BLOCKED"
    assert body["has_panel_review"] is True
    assert body["payload"]["panel"]["response_quality"]["confidence_score"] == 0.78


def test_upload_legacy_thrawn_verdict_still_marks_panel_review(ctx: Ctx) -> None:
    legacy = dict(ENHANCED_VERDICT)
    legacy["final_status"] = "THRAWN_BLOCKED"
    legacy["thrawn"] = legacy.pop("panel")
    resp = ctx.client.post("/verdicts", json={"payload": legacy})
    assert resp.status_code == 201, resp.text
    assert resp.json()["has_panel_review"] is True


def test_list_and_get_verdict(ctx: Ctx) -> None:
    created = ctx.client.post("/verdicts", json={"payload": CORE_VERDICT}).json()

    listing = ctx.client.get("/verdicts")
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 1
    assert rows[0]["id"] == created["id"]

    detail = ctx.client.get(f"/verdicts/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["payload"]["shot_id"] == "village_walk_001"


def test_get_missing_verdict_404(ctx: Ctx) -> None:
    resp = ctx.client.get("/verdicts/nonexistent")
    assert resp.status_code == 404
