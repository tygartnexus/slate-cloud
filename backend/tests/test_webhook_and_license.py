"""Payment webhook compatibility tests."""

from __future__ import annotations

from tests.conftest import Ctx


def test_stripe_webhook_is_disabled(ctx: Ctx) -> None:
    resp = ctx.client.post(
        "/webhooks/stripe",
        content=b'{"type":"checkout.session.completed"}',
        headers={"Stripe-Signature": "t=1,v1=dummy"},
    )

    assert resp.status_code == 410
    assert resp.json() == {
        "status": "payments_disabled",
        "detail": "Slate is free and open-source; Stripe webhooks are disabled.",
    }
