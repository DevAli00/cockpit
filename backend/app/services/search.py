from __future__ import annotations

from sqlalchemy import cast, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Account, Client, Fund, Entry, Goal, LearningItem, LearningPath, Milestone, Note, Project, Recurring, Task, Trip,
)
from app.schemas import SearchHit

_LIMIT = 8


def _like(q: str) -> str:
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def search(s: AsyncSession, q: str) -> list[SearchHit]:
    pat = _like(q.strip())

    def match(*cols):  # type: ignore[no-untyped-def]
        return or_(*(c.ilike(pat, escape="\\") for c in cols))

    hits: list[SearchHit] = []

    async def run(model, cols, build):  # type: ignore[no-untyped-def]
        rows = (await s.scalars(select(model).where(match(*cols)).limit(_LIMIT))).all()
        hits.extend(build(r) for r in rows)

    await run(Client, [Client.name], lambda r: SearchHit(kind="client", id=r.id, title=r.name))
    await run(
        Project,
        [Project.name, cast(Project.brief, String)],
        lambda r: SearchHit(kind="project", id=r.id, title=r.name, subtitle=r.status, project_id=r.id),
    )
    await run(
        Note, [Note.body],
        lambda r: SearchHit(kind="note", id=r.id, title=r.body[:120], subtitle=f"{r.kind} · {r.date}", project_id=r.project_id),
    )
    await run(
        Task, [Task.title, Task.note],
        lambda r: SearchHit(kind="task", id=r.id, title=r.title, subtitle=r.col, project_id=r.project_id),
    )
    await run(
        Entry, [Entry.label],
        lambda r: SearchHit(kind="entry", id=r.id, title=r.label, subtitle=f"{r.type} · {r.date}"),
    )
    await run(
        Recurring, [Recurring.label],
        lambda r: SearchHit(kind="recurring", id=r.id, title=r.label, subtitle=r.frequency),
    )
    await run(
        LearningPath, [LearningPath.name, LearningPath.description],
        lambda r: SearchHit(kind="path", id=r.id, title=r.name, subtitle=f"{r.kind} path"),
    )
    await run(
        Milestone, [Milestone.title, Milestone.notes],
        lambda r: SearchHit(kind="milestone", id=r.id, title=r.title, subtitle=f"{r.horizon} · {r.status}"),
    )
    await run(
        LearningItem, [LearningItem.title, LearningItem.author, LearningItem.notes],
        lambda r: SearchHit(kind="item", id=r.id, title=r.title, subtitle=f"{r.kind} · {r.status}"),
    )
    await run(
        Trip, [Trip.destination, Trip.notes],
        lambda r: SearchHit(kind="trip", id=r.id, title=r.destination, subtitle=r.status),
    )
    await run(
        Goal, [Goal.title, Goal.area],
        lambda r: SearchHit(kind="goal", id=r.id, title=r.title, subtitle=r.area),
    )
    await run(
        Account, [Account.name, Account.institution, Account.notes],
        lambda r: SearchHit(kind="account", id=r.id, title=r.name, subtitle=r.institution or r.type),
    )
    await run(
        Fund, [Fund.name, Fund.notes],
        lambda r: SearchHit(kind="fund", id=r.id, title=r.name, subtitle=f"{r.kind} fund"),
    )
    return hits
