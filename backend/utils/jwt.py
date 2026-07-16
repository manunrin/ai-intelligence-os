"""JWT token creation and verification."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from ..config import Settings, get_settings


def create_access_token(user_id: str, settings: Settings | None = None) -> str:
    """Create a signed JWT access token with user UUID as subject.

    The token payload contains:
    - sub: user UUID
    - exp: expiry timestamp
    """
    if settings is None:
        settings = get_settings()

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> dict | None:
    """Decode and verify a JWT access token.

    Returns the payload dict on success, or None if invalid/expired.
    """
    if settings is None:
        settings = get_settings()

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None
