"""Verdict upload, list, and detail endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai_response_quality import (
    ResponseQualityValidationError,
    validate_verdict_response_quality,
)
from app.auth.clerk import current_account
from app.db import get_db
from app.models import Account, VerdictRecord
from app.schemas import VerdictDetail, VerdictSummary, VerdictUploadRequest

router = APIRouter(prefix="/verdicts", tags=["verdicts"])


@router.post("", response_model=VerdictDetail, status_code=status.HTTP_201_CREATED)
def upload_verdict(
    body: VerdictUploadRequest,
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> VerdictDetail:
    """Accept a verdict JSON from the Slate CLI and persist it.

    The body MAY be the full payload directly, or wrapped under ``payload``;
    we accept either to be tolerant of the CLI's evolution.
    """
    raw_payload = body.payload or body.model_dump(exclude_none=True)
    try:
        validate_verdict_response_quality(raw_payload)
    except ResponseQualityValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "verdict response_quality contract failed",
                "issues": exc.issues,
            },
        ) from exc

    shot_id = (
        body.shot_id
        or raw_payload.get("shot_id")
        or _extract_nested(raw_payload, "core", "shot_id")
        or "(unknown)"
    )
    final_status = (
        body.final_status
        or raw_payload.get("final_status")
        or _extract_nested(raw_payload, "status")
        or "UNKNOWN"
    )
    has_panel_review = (
        "final_status" in raw_payload
        or "panel" in raw_payload
        or "thrawn" in raw_payload
    )

    record = VerdictRecord(
        account_id=account.id,
        shot_id=shot_id,
        final_status=final_status,
        has_panel_review=has_panel_review,
        payload=raw_payload,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return VerdictDetail(
        id=record.id,
        shot_id=record.shot_id,
        final_status=record.final_status,
        has_panel_review=record.has_panel_review,
        submitted_at=record.submitted_at,
        payload=record.payload,
    )


@router.get("", response_model=list[VerdictSummary])
def list_verdicts(
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> list[VerdictSummary]:
    q = (
        db.query(VerdictRecord)
        .filter(VerdictRecord.account_id == account.id)
        .order_by(VerdictRecord.submitted_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        VerdictSummary(
            id=r.id,
            shot_id=r.shot_id,
            final_status=r.final_status,
            has_panel_review=r.has_panel_review,
            submitted_at=r.submitted_at,
        )
        for r in q.all()
    ]


@router.get("/{verdict_id}", response_model=VerdictDetail)
def get_verdict(
    verdict_id: str,
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> VerdictDetail:
    record = (
        db.query(VerdictRecord)
        .filter(
            VerdictRecord.id == verdict_id,
            VerdictRecord.account_id == account.id,
        )
        .one_or_none()
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "verdict not found")
    return VerdictDetail(
        id=record.id,
        shot_id=record.shot_id,
        final_status=record.final_status,
        has_panel_review=record.has_panel_review,
        submitted_at=record.submitted_at,
        payload=record.payload,
    )


def _extract_nested(d: dict[str, Any], *keys: str) -> Any | None:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur
