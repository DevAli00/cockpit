from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task
from app.domain.tasks import (
    TaskColumn,
    done_at_for_move,
    is_visible_on_board,
    needs_rebalance,
    position_between,
)
from app.services import crud
from app.services.errors import InvalidError


async def list_tasks(s: AsyncSession, *, include_archived: bool) -> list[Task]:
    tasks = await crud.list_all(s, Task, Task.position, Task.created_at)
    if include_archived:
        return tasks
    now = datetime.now(UTC)
    return [t for t in tasks if is_visible_on_board(t.col, t.done_at, now)]  # type: ignore[arg-type]


async def create_task(s: AsyncSession, data: dict[str, Any]) -> Task:
    top = await s.scalar(select(func.max(Task.position)).where(Task.col == data["col"]))
    done_at = datetime.now(UTC) if data["col"] == "done" else None
    return await crud.create(
        s, Task, {**data, "position": position_between(top, None), "done_at": done_at}
    )


async def _column(s: AsyncSession, col: str, exclude: uuid.UUID) -> list[Task]:
    stmt = select(Task).where(Task.col == col, Task.id != exclude).order_by(Task.position, Task.created_at)
    return list((await s.scalars(stmt)).all())


async def move_task(
    s: AsyncSession, task_id: uuid.UUID, col: TaskColumn, before_id: uuid.UUID | None
) -> Task:
    task = await crud.get_or_404(s, Task, task_id)
    others = await _column(s, col, task.id)

    index = len(others)
    if before_id is not None:
        index = next((i for i, t in enumerate(others) if t.id == before_id), -1)
        if index < 0:
            raise InvalidError("before_id must be a different task in the target column")

    prev = others[index - 1].position if index > 0 else None
    nxt = others[index].position if index < len(others) else None
    if prev is not None and nxt is not None and (prev >= nxt or needs_rebalance(prev, nxt)):
        # Repeated squeezing exhausted float precision: renumber the whole column once.
        ordered = [*others[:index], task, *others[index:]]
        for i, t in enumerate(ordered, start=1):
            t.position = float(i)
    else:
        task.position = position_between(prev, nxt)

    task.done_at = done_at_for_move(task.col, col, task.done_at, datetime.now(UTC))  # type: ignore[arg-type]
    task.col = col
    await s.commit()
    return task
