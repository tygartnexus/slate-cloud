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
