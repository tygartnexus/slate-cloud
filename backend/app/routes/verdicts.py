"""Verdict upload, list, and detail endpoints."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai_response_quality import (
    ResponseQualityValidationError,
    validate_verdict_response_quality,
)
from app.auth.clerk import current_account
from app.config import get_settings
from app.db import get_db
from app.models import Account, VerdictRecord
from app.schemas import VerdictDetail, VerdictSummary, VerdictUploadRequest

router = APIRouter(prefix="/verdicts", tags=["verdicts"])
SENSITIVE_KEY_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "credential",
    "password",
    "passwd",
    "private_key",
    "secret",
    "session_key",
    "token",
)
RAW_OUTPUT_KEYS = {"raw_signals", "raw_response", "provider_outputs"}
REDACTED_VALUE = "[redacted]"


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
    _enforce_payload_size(raw_payload)
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
        payload=_redact_sensitive_payload(raw_payload),
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


def _enforce_payload_size(payload: dict[str, Any]) -> None:
    max_bytes = get_settings().VERDICT_MAX_PAYLOAD_BYTES
    payload_bytes = len(
        json.dumps(payload, default=str, separators=(",", ":")).encode("utf-8")
    )
    if payload_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"verdict payload exceeds {max_bytes} bytes",
        )


def _redact_sensitive_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text) or key_text in RAW_OUTPUT_KEYS:
                redacted[key_text] = REDACTED_VALUE
            else:
                redacted[key_text] = _redact_sensitive_payload(item)
        return redacted
    if isinstance(value, str) and _looks_like_secret(value):
        return REDACTED_VALUE
    if isinstance(value, list):
        return [_redact_sensitive_payload(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(marker in normalized for marker in SENSITIVE_KEY_MARKERS)


def _looks_like_secret(value: str) -> bool:
    compact = value.strip()
    if len(compact) < 24:
        return False
    lower = compact.lower()
    secret_prefixes = (
        "sk_live_",
        "rk_live_",
        "pk_live_",
        "sk_test_",
        "github_pat_",
        "ghp_",
        "gho_",
        "ghu_",
        "ghs_",
        "ghr_",
        "xoxb-",
        "xoxa-",
        "xoxp-",
    )
    if lower.startswith(secret_prefixes):
        return True
    if compact.startswith(("AKIA", "ASIA")) and len(compact) >= 20:
        return True
    if compact.startswith("AIza") and len(compact) >= 39:
        return True
    if "-----BEGIN " in compact and " PRIVATE KEY-----" in compact:
        return True
    return False
