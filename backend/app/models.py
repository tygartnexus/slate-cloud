"""SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_str() -> str:
    return uuid4().hex


class Account(Base):
    """One Clerk user -> one Slate account."""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid_str)
    clerk_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    verdicts: Mapped[list["VerdictRecord"]] = relationship(back_populates="account")


class VerdictRecord(Base):
    __tablename__ = "verdicts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid_str)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    shot_id: Mapped[str] = mapped_column(String(255), index=True)
    final_status: Mapped[str] = mapped_column(String(32), index=True)
    has_panel_review: Mapped[bool] = mapped_column(default=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)  # the full verdict JSON
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    account: Mapped[Account] = relationship(back_populates="verdicts")


Index(
    "ix_verdicts_account_submitted",
    VerdictRecord.account_id,
    VerdictRecord.submitted_at.desc(),
)
