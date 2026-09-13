from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from backend.app.core.config import settings


def create_access_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generate a signed short-lived JWT Access Token.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(subject),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        **(claims or {})
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generate a signed long-lived JWT Refresh Token.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(subject),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        **(claims or {})
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: Optional[str] = "access") -> Dict[str, Any]:
    """
    Decode and validate JWT signature, expiration, and token type.
    Raises:
        jwt.ExpiredSignatureError: If token expired
        jwt.InvalidTokenError: If invalid signature or malformed token
        ValueError: If token type mismatch
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat"]}
    )

    if expected_type and payload.get("type") != expected_type:
        raise ValueError(f"Invalid token type: expected '{expected_type}', got '{payload.get('type')}'")

    return payload
