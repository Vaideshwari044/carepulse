"""Security & authentication utilities for CarePulse."""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    pw_bytes = password.encode("utf-8")
    # Truncate if > 72 bytes per bcrypt spec
    if len(pw_bytes) > 72:
        pw_bytes = pw_bytes[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    try:
        pw_bytes = plain_password.encode("utf-8")
        if len(pw_bytes) > 72:
            pw_bytes = pw_bytes[:72]
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode JWT access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid access token: {e}") from e


def create_refresh_token() -> tuple[str, str]:
    """Create raw refresh token and its SHA256 hash. Returns (raw_token, hashed_token)."""
    raw_token = secrets.token_urlsafe(64)
    hashed = hash_refresh_token(raw_token)
    return raw_token, hashed


def hash_refresh_token(raw_token: str) -> str:
    """Hash refresh token with SHA256."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
