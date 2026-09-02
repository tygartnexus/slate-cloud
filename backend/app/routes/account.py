"""Account endpoints."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.clerk import current_account
from app.db import get_db
from app.models import Account, VerdictRecord
from app.schemas import AccountDeletionReceipt, AccountInfo

if TYPE_CHECKING:
    from sqlalchemy import CursorResult

router = APIRouter(prefix="/account", tags=["account"])

LEGACY_ARCHIVE_TABLE = "legacy_licenses_archive"
ERASED_TOKEN_MARKER = "[erased]"

# Rows are streamed in batches so an account with a large verdict history cannot
# materialise the whole export in memory at once.
EXPORT_BATCH_SIZE = 25


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


@router.get("/export")
def export_account(
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream everything this account holds, as newline-delimited JSON.

    NDJSON rather than one JSON document on purpose: verdict payloads are capped
    individually but not in aggregate, so a single document would have to be
    either bounded (silently incomplete) or fully buffered (unbounded memory).
    Streaming line-by-line is neither.

    The first line is a metadata header carrying ``verdict_count``. A consumer
    compares it against the number of verdict lines received, so a connection
    that drops mid-stream is detectable rather than silently short.
    """
    verdict_count = (
        db.query(VerdictRecord).filter(VerdictRecord.account_id == account.id).count()
    )
    filename = f"slate-cloud-export-{account.id}.ndjson"
    return StreamingResponse(
        _export_lines(db, account, verdict_count),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _export_lines(db: Session, account: Account, verdict_count: int) -> Iterator[str]:
    header: dict[str, Any] = {
        "type": "export_metadata",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "id": account.id,
            "email": account.email,
            "created_at": account.created_at.isoformat(),
        },
        "verdict_count": verdict_count,
        "note": (
            "Compare verdict_count against the number of type=verdict lines to "
            "confirm the export is complete."
        ),
    }
    yield json.dumps(header, default=str) + "\n"

    query = (
        db.query(VerdictRecord)
        .filter(VerdictRecord.account_id == account.id)
        .order_by(VerdictRecord.submitted_at.desc())
        .yield_per(EXPORT_BATCH_SIZE)
    )
    for record in query:
        yield (
            json.dumps(
                {
                    "type": "verdict",
                    "id": record.id,
                    "shot_id": record.shot_id,
                    "final_status": record.final_status,
                    "has_panel_review": record.has_panel_review,
                    "submitted_at": record.submitted_at.isoformat(),
                    "payload": record.payload,
                },
                default=str,
            )
            + "\n"
        )


@router.delete("", response_model=AccountDeletionReceipt)
def delete_account(
    confirm: str = Query(
        ...,
        description="Must equal your own account id, as returned by GET /account.",
    ),
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> AccountDeletionReceipt:
    """Erase this account and its verdicts. Irreversible.

    ``confirm`` must carry the caller's own account id. That makes the call
    impossible to trigger by accident, and impossible to script blindly without
    first reading GET /account.

    Legacy archive rows are kept but stripped: the signed license token and
    Stripe subscription id are erased and the account link is dropped, so the
    fact a license existed stays auditable while the data identifying a person
    does not. See docs/privacy-and-security.md.

    This erases Slate Cloud's data only. The Clerk user is untouched, so signing
    in again creates a fresh, empty account with a new id.
    """
    if confirm != account.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "confirm must equal your own account id; "
                "fetch it from GET /account first"
            ),
        )

    # One transaction: an account is either fully erased or not touched at all.
    try:
        archived = _anonymise_legacy_archive(db, account.id)
        verdicts_deleted = (
            db.query(VerdictRecord)
            .filter(VerdictRecord.account_id == account.id)
            .delete(synchronize_session=False)
        )
        db.delete(account)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AccountDeletionReceipt(
        status="account_deleted",
        account_id=confirm,
        verdicts_deleted=verdicts_deleted,
        legacy_licenses_anonymised=archived,
        detail=(
            "Slate Cloud data erased. Your Clerk login still exists; signing in "
            "again creates a new empty account."
        ),
    )


def _anonymise_legacy_archive(db: Session, account_id: str) -> int:
    """Strip identifying fields from the account's archive rows, keep the rows.

    The table is deliberately unmapped (see migrations/autogen.py), so this is
    raw SQL with bound parameters rather than an ORM update.
    """
    inspector = sa.inspect(db.get_bind())
    if LEGACY_ARCHIVE_TABLE not in set(inspector.get_table_names()):
        return 0
    # Session.execute is typed as Result; a DML statement really returns a
    # CursorResult, which is where rowcount lives.
    result = cast(
        "CursorResult[Any]",
        db.execute(
            sa.text(
                f"UPDATE {LEGACY_ARCHIVE_TABLE} "
                "SET token = :marker, stripe_subscription_id = NULL, account_id = NULL "
                "WHERE account_id = :account_id"
            ),
            {"marker": ERASED_TOKEN_MARKER, "account_id": account_id},
        ),
    )
    return int(result.rowcount or 0)


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
