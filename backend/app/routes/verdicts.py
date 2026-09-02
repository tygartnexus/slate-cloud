"""Verdict upload, list, and detail endpoints."""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
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

# Whole-segment markers. Matching these as bare substrings redacts ordinary
# telemetry (token_count, total_tokens), so keys are split into segments before
# comparison.
SENSITIVE_KEY_SEGMENTS = frozenset(
    {
        "apikey",
        "authorization",
        "bearer",
        "credential",
        "credentials",
        "password",
        "passwd",
        "secret",
        "secrets",
        "token",
        "tokens",
    }
)
# Substrings that stay unambiguous however the key is segmented.
SENSITIVE_KEY_PHRASES = (
    "api_key",
    "access_key",
    "private_key",
    "secret_key",
    "session_key",
)
# Model-usage metrics that segment-match token/tokens but carry no secret.
METRIC_KEY_ALLOWLIST = frozenset(
    {
        "cached_tokens",
        "completion_tokens",
        "input_tokens",
        "max_tokens",
        "output_tokens",
        "prompt_tokens",
        "reasoning_tokens",
        "token_count",
        "token_usage",
        "tokens_per_second",
        "tokens_used",
        "total_tokens",
    }
)
RAW_OUTPUT_KEYS = {"raw_signals", "raw_response", "provider_outputs"}
REDACTED_VALUE = "[redacted]"
KEY_SEGMENT_SPLIT = re.compile(r"[^a-z0-9]+")

# Bounds the recursive redaction and validation walks. Deeply nested JSON is
# malformed for a verdict and would otherwise exhaust the interpreter stack and
# surface to the caller as a 500.
MAX_PAYLOAD_DEPTH = 64

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


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
    # Depth first: the size check serializes the payload, and the validation and
    # redaction walks recurse, so all three need a bounded structure.
    _enforce_payload_depth(raw_payload)
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

    record = VerdictRecord(
        account_id=account.id,
        shot_id=shot_id,
        final_status=final_status,
        has_panel_review=_detect_panel_review(raw_payload),
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
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
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


@router.delete("/{verdict_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_verdict(
    verdict_id: str,
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> None:
    """Delete one of the caller's own verdicts.

    Scoped by account_id as well as id, so a verdict belonging to someone else
    is a 404 rather than a 403 -- the caller learns nothing about whether the id
    exists.
    """
    deleted = (
        db.query(VerdictRecord)
        .filter(
            VerdictRecord.id == verdict_id,
            VerdictRecord.account_id == account.id,
        )
        .delete(synchronize_session=False)
    )
    if not deleted:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "verdict not found")
    db.commit()


def _detect_panel_review(payload: dict[str, Any]) -> bool:
    """True only when the payload actually carries a Panel review block.

    final_status is present on virtually every verdict, so treating it as Panel
    evidence marked every upload as reviewed. Require a non-empty Panel block
    instead: a run may report a panel summary and response_quality without
    per-persona detail, and that is still reviewable evidence to surface. The
    legacy key is accepted for backward compatibility with older verdict JSON.
    """
    return any(
        isinstance(payload.get(key), dict) and payload[key]
        for key in ("panel", "thrawn")
    )


def _extract_nested(d: dict[str, Any], *keys: str) -> Any | None:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _enforce_payload_depth(payload: dict[str, Any]) -> None:
    """Reject over-nested payloads using an iterative walk.

    Deliberately not recursive: this gate protects the recursive walks that
    follow, so it cannot rely on the stack itself.
    """
    stack: list[tuple[Any, int]] = [(payload, 1)]
    while stack:
        node, depth = stack.pop()
        if depth > MAX_PAYLOAD_DEPTH:
            raise HTTPException(
                status_code=422,
                detail=f"verdict payload nesting exceeds {MAX_PAYLOAD_DEPTH} levels",
            )
        if isinstance(node, dict):
            stack.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, list):
            stack.extend((child, depth + 1) for child in node)


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
    if normalized in METRIC_KEY_ALLOWLIST:
        return False
    if any(phrase in normalized for phrase in SENSITIVE_KEY_PHRASES):
        return True
    segments = {segment for segment in KEY_SEGMENT_SPLIT.split(normalized) if segment}
    return bool(segments & SENSITIVE_KEY_SEGMENTS)


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
    return "-----BEGIN " in compact and " PRIVATE KEY-----" in compact
