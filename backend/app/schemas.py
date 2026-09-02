"""Pydantic request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VerdictUploadRequest(BaseModel):
    """The body the Slate CLI POSTs to /verdicts."""

    model_config = ConfigDict(extra="allow")

    shot_id: str | None = None
    final_status: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class VerdictSummary(BaseModel):
    id: str
    shot_id: str
    final_status: str
    has_panel_review: bool
    submitted_at: datetime


class VerdictDetail(VerdictSummary):
    payload: dict[str, Any]


class AccountInfo(BaseModel):
    id: str
    email: str
    verdict_count: int


class AccountDeletionReceipt(BaseModel):
    """What an account deletion actually erased.

    Returned instead of a bare 204 so the caller has a record of the scope of an
    irreversible action.
    """

    status: str
    account_id: str
    verdicts_deleted: int
    legacy_licenses_anonymised: int
    detail: str
