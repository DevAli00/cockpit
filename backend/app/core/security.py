"""Password hashing and signed session tokens. No framework imports."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()
_ALGORITHM = "HS256"


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(subject: str, secret: str, ttl: timedelta) -> str:
    now = datetime.now(UTC)
    return jwt.encode({"sub": subject, "iat": now, "exp": now + ttl}, secret, _ALGORITHM)


def decode_access_token(token: str, secret: str) -> str:
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    return str(payload["sub"])
