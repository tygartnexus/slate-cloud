"""Payment webhook compatibility routes.

Slate Cloud no longer mints paid licenses. The Stripe endpoint remains as an
explicit disabled response for stale webhook configurations.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookDisabledResponse(BaseModel):
    status: str
    detail: str


@router.post(
    "/stripe",
    response_model=WebhookDisabledResponse,
    status_code=status.HTTP_410_GONE,
)
def stripe_webhook() -> WebhookDisabledResponse:
    return WebhookDisabledResponse(
        status="payments_disabled",
        detail="Slate is free and open-source; Stripe webhooks are disabled.",
    )
