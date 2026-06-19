"""Account endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.clerk import current_account
from app.db import get_db
from app.models import Account, VerdictRecord
from app.schemas import AccountInfo

router = APIRouter(prefix="/account", tags=["account"])


class FreeAccessResponse(BaseModel):
    status: str
    detail: str


@router.get("", response_model=AccountInfo)
def get_account(
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> AccountInfo:
    verdict_count = (
        db.query(VerdictRecord).filter(VerdictRecord.account_id == account.id).count()
    )
    return AccountInfo(
        id=account.id,
        email=account.email,
        verdict_count=verdict_count,
    )


@router.get(
    "/license",
    response_model=FreeAccessResponse,
    status_code=status.HTTP_410_GONE,
)
def get_active_license(
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> FreeAccessResponse:
    """Compatibility endpoint for older clients.

    Slate no longer requires activation tokens, so the dashboard should not call
    this endpoint for new flows.
    """
    _ = (account, db)
    return FreeAccessResponse(
        status="license_not_required",
        detail="Slate features are free and open-source; no activation token is needed.",
    )
