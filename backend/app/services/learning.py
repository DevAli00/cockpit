from __future__ import annotations

import uuid
from collections import Counter
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningItem, LearningPath, Milestone
from app.domain.learning import is_overdue, item_percent, next_item_status, path_progress
from app.schemas_life import ItemOut, LearningOverview, MilestoneOut, PathOut
from app.services import crud


def milestone_out(m: Milestone, today: date) -> MilestoneOut:
    out = MilestoneOut.model_validate(m)
    return out.model_copy(update={"overdue": is_overdue(m.status, m.due, today)})  # type: ignore[arg-type]


def item_out(i: LearningItem) -> ItemOut:
    out = ItemOut.model_validate(i)
    return out.model_copy(update={"percent": item_percent(i.progress_current, i.progress_total)})


async def list_paths(s: AsyncSession) -> list[PathOut]:
    paths = (await s.scalars(select(LearningPath).order_by(LearningPath.kind, LearningPath.created_at))).all()
    statuses: dict[uuid.UUID, list[str]] = {}
    for pid, status in (await s.execute(select(Milestone.path_id, Milestone.status))).all():
        statuses.setdefault(pid, []).append(status)
    out = []
    for p in paths:
        sts = statuses.get(p.id, [])
        out.append(
            PathOut.model_validate(p).model_copy(
                update={
                    "milestones_total": len(sts),
                    "milestones_done": sts.count("done"),
                    "progress": float(path_progress(sts)),  # type: ignore[arg-type]
                }
            )
        )
    return out


async def path_out(s: AsyncSession, path: LearningPath) -> PathOut:
    return next(p for p in await list_paths(s) if p.id == path.id)


async def list_milestones(
    s: AsyncSession, today: date, *, path_id: uuid.UUID | None = None, horizon: str | None = None
) -> list[MilestoneOut]:
    stmt = select(Milestone).order_by(Milestone.due.is_(None), Milestone.due, Milestone.created_at)
    if path_id:
        stmt = stmt.where(Milestone.path_id == path_id)
    if horizon:
        stmt = stmt.where(Milestone.horizon == horizon)
    return [milestone_out(m, today) for m in (await s.scalars(stmt)).all()]


def _with_lifecycle(old: dict[str, Any], data: dict[str, Any], today: date) -> dict[str, Any]:
    """Apply progress -> status and started/finished date rules to an item create/update."""
    merged = {**old, **data}
    status = merged["status"]
    if "status" not in data:
        status = next_item_status(status, merged["progress_current"], merged["progress_total"])
    out = {**data, "status": status}
    if status in ("in_progress", "done") and merged.get("started") is None:
        out["started"] = today
    if status == "done" and old.get("status") != "done" and "finished" not in data:
        out["finished"] = today
    if status != "done" and "finished" not in data:
        out["finished"] = None
    return out


_ITEM_DEFAULTS: dict[str, Any] = {
    "status": "backlog", "progress_current": 0, "progress_total": None, "started": None, "finished": None,
}


async def create_item(s: AsyncSession, data: dict[str, Any], today: date) -> LearningItem:
    # On create, a missing date and an explicit null mean the same thing: not given yet.
    given = {k: v for k, v in data.items() if not (k in ("started", "finished") and v is None)}
    return await crud.create(s, LearningItem, {**data, **_with_lifecycle(_ITEM_DEFAULTS, given, today)})


async def update_item(s: AsyncSession, item: LearningItem, data: dict[str, Any], today: date) -> LearningItem:
    old = {k: getattr(item, k) for k in ("status", "progress_current", "progress_total", "started", "finished")}
    return await crud.update(s, item, _with_lifecycle(old, data, today))


async def list_items(
    s: AsyncSession, *, kind: str | None, status: str | None, path_id: uuid.UUID | None
) -> list[LearningItem]:
    stmt = select(LearningItem).order_by(LearningItem.created_at.desc(), LearningItem.id)
    if kind:
        stmt = stmt.where(LearningItem.kind == kind)
    if status:
        stmt = stmt.where(LearningItem.status == status)
    if path_id:
        stmt = stmt.where(LearningItem.path_id == path_id)
    return list((await s.scalars(stmt)).all())


async def overview(s: AsyncSession, today: date) -> LearningOverview:
    items = (await s.scalars(select(LearningItem))).all()
    done = [i for i in items if i.status == "done"]
    return LearningOverview(
        done_by_kind=dict(Counter(i.kind for i in done)),
        done_this_year=sum(1 for i in done if i.finished and i.finished.year == today.year),
        in_progress=sum(1 for i in items if i.status == "in_progress"),
        backlog=sum(1 for i in items if i.status == "backlog"),
    )
