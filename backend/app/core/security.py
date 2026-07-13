"""Security primitives: password hashing, JWT tokens, symmetric encryption.

- Passwords are hashed with bcrypt (passlib).
- Access/refresh tokens are signed JWTs; refresh tokens carry a ``jti`` and
  ``fam`` (family id) to support server-side rotation and reuse detection.
- Sensitive third-party secrets (e.g. Google OAuth refresh tokens) are
  encrypted at rest with Fernet using ``ENCRYPTION_KEY``.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, Literal

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

TokenType = Literal["access", "refresh"]


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def _prehash(password: str) -> bytes:
    """Collapse a password to a fixed 44-byte token.

    bcrypt silently truncates inputs beyond 72 bytes (and modern versions raise
    on them). Pre-hashing with SHA-256 + base64 yields a constant-length secret
    that still depends on the entire password, so arbitrarily long passwords
    are supported safely.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# JWT tokens
# --------------------------------------------------------------------------
def _encode(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, payload


def create_access_token(subject: str | uuid.UUID) -> str:
    token, _ = _encode(
        str(subject),
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return token


def create_refresh_token(
    subject: str | uuid.UUID,
    *,
    family_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return ``(token, payload)``; payload exposes ``jti``/``fam``/``exp``."""
    fam = family_id or uuid.uuid4().hex
    return _encode(
        str(subject),
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra={"fam": fam},
    )


def decode_token(token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired", error_code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid token", error_code="invalid_token") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type", error_code="invalid_token_type")
    return payload


# --------------------------------------------------------------------------
# Random secrets / hashing
# --------------------------------------------------------------------------
def generate_state_token() -> str:
    """Opaque, URL-safe random token (OAuth state / CSRF nonce)."""
    return secrets.token_urlsafe(32)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# --------------------------------------------------------------------------
# Symmetric encryption (tokens at rest)
# --------------------------------------------------------------------------
@lru_cache
def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not configured; cannot encrypt secrets.")
    # Accept a raw 32-byte key or an already-formatted Fernet key.
    try:
        return Fernet(key)
    except (ValueError, TypeError):
        digest = hashlib.sha256(key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
