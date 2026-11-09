from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.models import User

# Verified against when the email is unknown, so both failure paths cost the same time.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def _norm(email: str) -> str:
    return email.strip().lower()


async def ensure_owner(s: AsyncSession, email: str, password: str) -> User:
    """Make the single owner account match the environment (so editing .env resets access)."""
    email = _norm(email)
    user = (await s.scalars(select(User).limit(1))).first()
    if user is None:
        user = User(email=email, password_hash=hash_password(password))
        s.add(user)
    else:
        user.email = email
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
    await s.commit()
    return user


async def authenticate(s: AsyncSession, email: str, password: str) -> User | None:
    user = (await s.scalars(select(User).where(User.email == _norm(email)))).first()
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    return user if user and ok else None


async def owner(s: AsyncSession) -> User | None:
    return (await s.scalars(select(User).limit(1))).first()
