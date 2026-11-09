from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import InvalidTokenError, decode_access_token
from app.db.models import User

COOKIE = "cockpit_session"


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]
Config = Annotated[Settings, Depends(get_settings_dep)]


async def current_user(request: Request, session: Session, settings: Config) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    token = request.cookies.get(COOKIE)
    if not token:
        raise unauthorized
    try:
        user_id = uuid.UUID(decode_access_token(token, settings.secret_key))
    except (InvalidTokenError, ValueError):
        raise unauthorized from None
    user = await session.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(current_user)]
