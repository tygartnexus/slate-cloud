"""Regression tests for the verdict upload/list hardening fixes."""

from __future__ import annotations

import json

import pytest

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


def _persona(name: str = "animator") -> dict:
    return {
        "name": name,
        "publish_ready": False,
        "summary": "Motion risk found.",
        "flags": [],
    }


class TestPanelDetection:
    """has_panel_review used to be true whenever final_status was present."""

    def test_verdict_without_panel_is_not_marked_reviewed(self, ctx) -> None:
        resp = ctx.client.post(
            "/verdicts",
            json={
                "payload": {
                    "shot_id": "shot_no_panel",
                    "final_status": "PASS",
                    "response_quality": RESPONSE_QUALITY,
                }
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["has_panel_review"] is False

    def test_empty_panel_block_is_not_marked_reviewed(self, ctx) -> None:
        resp = ctx.client.post(
            "/verdicts",
            json={
                "payload": {
                    "final_status": "PASS",
                    "panel": {},
                    "response_quality": RESPONSE_QUALITY,
                }
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["has_panel_review"] is False

    def test_panel_summary_without_personas_is_still_reviewed(self, ctx) -> None:
        """A Panel run can report a summary and response_quality with no
        per-persona detail; that is still evidence the detail page renders."""
        resp = ctx.client.post(
            "/verdicts",
            json={
                "payload": {
                    "final_status": "PANEL_BLOCKED",
                    "panel": {
                        "publish_ready": False,
                        "per_persona": [],
                        "summary": "animator blocks",
                        "response_quality": RESPONSE_QUALITY,
                    },
                    "response_quality": RESPONSE_QUALITY,
                }
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["has_panel_review"] is True

    def test_panel_with_personas_is_marked_reviewed(self, ctx) -> None:
        resp = ctx.client.post(
            "/verdicts",
            json={
                "payload": {
                    "final_status": "PANEL_BLOCKED",
                    "panel": {"per_persona": [_persona()]},
                    "response_quality": RESPONSE_QUALITY,
                }
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["has_panel_review"] is True

    def test_legacy_panel_key_is_still_honoured(self, ctx) -> None:
        resp = ctx.client.post(
            "/verdicts",
            json={
                "payload": {
                    "final_status": "PANEL_BLOCKED",
                    "thrawn": {"per_persona": [_persona("director")]},
                    "response_quality": RESPONSE_QUALITY,
                }
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["has_panel_review"] is True


class TestPaginationBounds:
    @pytest.mark.parametrize(
        "query",
        ["limit=999999999", "limit=0", "limit=-5", "offset=-1"],
    )
    def test_out_of_range_pagination_is_rejected(self, ctx, query: str) -> None:
        assert ctx.client.get(f"/verdicts?{query}").status_code == 422

    def test_in_range_pagination_is_accepted(self, ctx) -> None:
        assert ctx.client.get("/verdicts?limit=200&offset=0").status_code == 200


class TestPayloadDepth:
    def test_deeply_nested_payload_is_rejected_not_a_500(self, ctx) -> None:
        """A ~3KB body used to return 500 by exhausting the interpreter stack."""
        depth = 500
        body = (
            '{"payload":'
            + '{"n":' * depth
            + json.dumps({"response_quality": RESPONSE_QUALITY})
            + "}" * depth
            + "}"
        )
        assert len(body) < 524288
        resp = ctx.client.post(
            "/verdicts", content=body, headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 422, resp.text
        assert "nesting" in json.dumps(resp.json())

    def test_payload_within_depth_limit_is_accepted(self, ctx) -> None:
        payload: dict = {"response_quality": RESPONSE_QUALITY}
        for _ in range(20):
            payload = {"n": payload}
        payload["final_status"] = "PASS"
        resp = ctx.client.post("/verdicts", json={"payload": payload})
        assert resp.status_code == 201, resp.text


class TestRedaction:
    def test_usage_metrics_are_preserved(self, ctx) -> None:
        """token_count/total_tokens used to be destroyed by substring matching."""
        resp = ctx.client.post(
            "/verdicts",
            json={
                "payload": {
                    "response_quality": RESPONSE_QUALITY,
                    "usage": {
                        "token_count": 123,
                        "total_tokens": 9,
                        "prompt_tokens": 4,
                        "completion_tokens": 5,
                        "latency_ms": 40,
                    },
                }
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["payload"]["usage"] == {
            "token_count": 123,
            "total_tokens": 9,
            "prompt_tokens": 4,
            "completion_tokens": 5,
            "latency_ms": 40,
        }

    @pytest.mark.parametrize(
        "key",
        [
            "api_key",
            "apiKey",
            "X-Api-Key",
            "access_token",
            "refresh_token",
            "authorization",
            "password",
            "private_key",
            "client_secret",
        ],
    )
    def test_credential_keys_are_still_redacted(self, ctx, key: str) -> None:
        resp = ctx.client.post(
            "/verdicts",
            json={
                "payload": {
                    "response_quality": RESPONSE_QUALITY,
                    "provider": {key: "super-secret-value-goes-here"},
                }
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["payload"]["provider"][key] == "[redacted]"
