from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project
from app.services import crud


async def create_project(s: AsyncSession, data: dict[str, Any]) -> Project:
    """New projects take the smallest position minus one so they show on top."""
    lowest = await s.scalar(select(func.min(Project.position)))
    position = (lowest if lowest is not None else 1.0) - 1
    return await crud.create(s, Project, {**data, "position": position})


async def update_project(s: AsyncSession, project: Project, data: dict[str, Any]) -> Project:
    if "brief" in data and data["brief"] is not None:
        data = {**data, "brief": {**project.brief, **data["brief"]}}
    return await crud.update(s, project, data)
