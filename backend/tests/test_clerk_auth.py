"""Clerk JWT verification tests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.auth.clerk import _verify_clerk_jwt
from app.config import get_settings


@pytest.fixture
def rsa_keys() -> Iterator[tuple[rsa.RSAPrivateKey, str]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    yield private_key, public_pem
    get_settings.cache_clear()


def _token(private_key: rsa.RSAPrivateKey, **claims: object) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "user_123",
        "email": "user@example.com",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        **claims,
    }
    return pyjwt.encode(payload, private_key, algorithm="RS256")


def test_verify_clerk_jwt_accepts_configured_claims(
    monkeypatch: pytest.MonkeyPatch,
    rsa_keys: tuple[rsa.RSAPrivateKey, str],
) -> None:
    private_key, public_pem = rsa_keys
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", public_pem)
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example.test")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "slate-cloud")
    monkeypatch.setenv("CLERK_JWT_AUTHORIZED_PARTIES", "frontend-client,other")
    get_settings.cache_clear()

    claims = _verify_clerk_jwt(
        _token(
            private_key,
            iss="https://clerk.example.test",
            aud="slate-cloud",
            azp="frontend-client",
        )
    )

    assert claims["sub"] == "user_123"


@pytest.mark.parametrize(
    ("claim_overrides", "expected"),
    [
        (
            {
                "iss": "https://wrong.example.test",
                "aud": "slate-cloud",
                "azp": "frontend-client",
            },
            "Invalid issuer",
        ),
        (
            {
                "iss": "https://clerk.example.test",
                "aud": "wrong-audience",
                "azp": "frontend-client",
            },
            "Audience doesn't match",
        ),
        (
            {
                "iss": "https://clerk.example.test",
                "aud": "slate-cloud",
                "azp": "wrong-client",
            },
            "unauthorized authorized party",
        ),
    ],
)
def test_verify_clerk_jwt_rejects_wrong_configured_claims(
    monkeypatch: pytest.MonkeyPatch,
    rsa_keys: tuple[rsa.RSAPrivateKey, str],
    claim_overrides: dict[str, str],
    expected: str,
) -> None:
    private_key, public_pem = rsa_keys
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", public_pem)
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example.test")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "slate-cloud")
    monkeypatch.setenv("CLERK_JWT_AUTHORIZED_PARTIES", "frontend-client")
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        _verify_clerk_jwt(_token(private_key, **claim_overrides))

    assert exc_info.value.status_code == 401
    assert expected in str(exc_info.value.detail)


@pytest.mark.parametrize(
    ("removed_claim", "expected"),
    [
        ("sub", 'Token is missing the "sub" claim'),
        ("iat", 'Token is missing the "iat" claim'),
        ("exp", 'Token is missing the "exp" claim'),
    ],
)
def test_verify_clerk_jwt_requires_identity_and_time_claims(
    monkeypatch: pytest.MonkeyPatch,
    rsa_keys: tuple[rsa.RSAPrivateKey, str],
    removed_claim: str,
    expected: str,
) -> None:
    private_key, public_pem = rsa_keys
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", public_pem)
    get_settings.cache_clear()

    now = datetime.now(timezone.utc)
    claims = {
        "sub": "user_123",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.pop(removed_claim)

    with pytest.raises(HTTPException) as exc_info:
        _verify_clerk_jwt(pyjwt.encode(claims, private_key, algorithm="RS256"))

    assert exc_info.value.status_code == 401
    assert expected in str(exc_info.value.detail)


def test_verify_clerk_jwt_rejects_expired_token(
    monkeypatch: pytest.MonkeyPatch,
    rsa_keys: tuple[rsa.RSAPrivateKey, str],
) -> None:
    private_key, public_pem = rsa_keys
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", public_pem)
    get_settings.cache_clear()

    now = datetime.now(timezone.utc)
    token = _token(
        private_key,
        iat=now - timedelta(minutes=10),
        exp=now - timedelta(minutes=1),
    )

    with pytest.raises(HTTPException) as exc_info:
        _verify_clerk_jwt(token)

    assert exc_info.value.status_code == 401
    assert "Signature has expired" in str(exc_info.value.detail)
