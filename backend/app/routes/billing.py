"""Payment compatibility routes.

Slate Cloud is now free and open-source. These endpoints remain only so older
clients receive an explicit response instead of a 404 or an accidental payment
flow.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(prefix="/billing", tags=["billing"])


class PaymentsDisabledResponse(BaseModel):
    status: str
    detail: str


PAYMENTS_DISABLED = PaymentsDisabledResponse(
    status="payments_disabled",
    detail="Slate is free and open-source; checkout and billing are disabled.",
)


@router.post(
    "/checkout",
    response_model=PaymentsDisabledResponse,
    status_code=status.HTTP_410_GONE,
)
def create_checkout() -> PaymentsDisabledResponse:
    return PAYMENTS_DISABLED


@router.post(
    "/portal",
    response_model=PaymentsDisabledResponse,
    status_code=status.HTTP_410_GONE,
)
def create_portal() -> PaymentsDisabledResponse:
    return PAYMENTS_DISABLED
