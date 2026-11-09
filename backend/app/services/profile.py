from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile
from app.services import crud


async def get_profile(s: AsyncSession) -> Profile:
    profile = await s.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1)
        s.add(profile)
        await s.commit()
    return profile


async def update_profile(s: AsyncSession, data: dict[str, Any]) -> Profile:
    return await crud.update(s, await get_profile(s), data)
