from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings

settings = get_settings()


def create_access_token(user_id: int) -> str:
    """Create a signed JWT containing the user id."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "iat": datetime.now(UTC)}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> int:
    """Decode a JWT and return the user id. Raises jwt.PyJWTError on failure."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return int(payload["sub"])
