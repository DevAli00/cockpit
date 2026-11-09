from __future__ import annotations

from datetime import date
from typing import Any

from app.db.models import Goal
from app.domain.goals import expected_progress, goal_status, progress
from app.schemas_life import GoalOut
from app.services import crud
from app.services.errors import InvalidError

from sqlalchemy.ext.asyncio import AsyncSession


def goal_out(g: Goal, today: date) -> GoalOut:
    return GoalOut.model_validate(g).model_copy(
        update={
            "progress": float(progress(g.current, g.target)),
            "expected": float(expected_progress(g.start, g.deadline, today)),
            "status": goal_status(g.current, g.target, g.start, g.deadline, today),
        }
    )


async def update_goal(s: AsyncSession, goal: Goal, data: dict[str, Any]) -> Goal:
    if data.get("deadline", goal.deadline) <= data.get("start", goal.start):
        raise InvalidError("deadline must be after start")
    return await crud.update(s, goal, data)
