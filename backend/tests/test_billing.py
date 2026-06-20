"""Billing compatibility endpoint tests."""

from __future__ import annotations

from tests.conftest import Ctx


def test_checkout_is_disabled(ctx: Ctx) -> None:
    resp = ctx.client.post(
        "/billing/checkout",
        json={
            "tier": "pro",
            "cadence": "monthly",
            "success_url": "https://frontend.example.invalid/dashboard",
            "cancel_url": "https://frontend.example.invalid",
        },
    )

    assert resp.status_code == 410
    assert resp.json() == {
        "status": "payments_disabled",
        "detail": "Slate is free and open-source; checkout and billing are disabled.",
    }


def test_billing_portal_is_disabled(ctx: Ctx) -> None:
    resp = ctx.client.post("/billing/portal")

    assert resp.status_code == 410
    assert resp.json()["status"] == "payments_disabled"
