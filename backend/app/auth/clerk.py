"""Clerk JWT verification.

Clerk issues short-lived JWTs signed with RS256. We verify locally using the
public key from the Clerk dashboard (configured via ``CLERK_JWT_PUBLIC_KEY``).

If you'd rather call Clerk's `/sessions/verify` API, replace this with an
async httpx call — but verifying locally is faster, cheaper, and works offline
for development.
"""

from __future__ import annotations

from typing import Any

import jwt as pyjwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Account


def _verify_clerk_jwt(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.CLERK_JWT_PUBLIC_KEY:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "CLERK_JWT_PUBLIC_KEY not configured",
        )
    try:
        return pyjwt.decode(
            token,
            settings.CLERK_JWT_PUBLIC_KEY,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, f"invalid clerk jwt: {exc}"
        ) from exc


def current_account(
    authorization: str = Header(..., description="Bearer <clerk-jwt>"),
    db: Session = Depends(get_db),
) -> Account:
    """FastAPI dependency that returns the authenticated Account, creating one if first-seen."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1]
    claims = _verify_clerk_jwt(token)
    clerk_user_id = str(claims.get("sub", ""))
    email = str(claims.get("email", "") or claims.get("email_address", ""))
    if not clerk_user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "jwt missing sub")

    account = (
        db.query(Account).filter(Account.clerk_user_id == clerk_user_id).one_or_none()
    )
    if account is None:
        account = Account(clerk_user_id=clerk_user_id, email=email)
        db.add(account)
        db.commit()
        db.refresh(account)
    return account
