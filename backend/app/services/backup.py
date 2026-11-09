from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Account, BalanceSnapshot, Client, Fund, FundContribution, Entry, Goal, LearningItem, LearningPath, Metric, Milestone, Note, Project, Recurring, Task,
    Trip, TripItem, WeekCheck, WeekValue,
)
from app.schemas import ProfileOut
from app.schemas_backup import Backup, WeekCheckBackup
from app.services import crud
from app.services.errors import InvalidError
from app.services.profile import get_profile

# Children first, so deletes never trip over foreign keys.
_WIPE_ORDER = (
    FundContribution, Fund, BalanceSnapshot, Account, WeekValue, WeekCheck, Metric, Goal, TripItem, Trip, LearningItem, Milestone, LearningPath,
    Note, Task, Entry, Recurring, Project, Client,
)


async def export_all(s: AsyncSession) -> Backup:
    async def rows(model, *order):  # type: ignore[no-untyped-def]
        return await crud.list_all(s, model, *order)

    values: dict = {}
    for v in (await s.scalars(select(WeekValue))).all():
        values.setdefault(v.check_id, {})[v.metric_id] = v.value
    checks = [
        WeekCheckBackup(
            id=c.id, week_start=c.week_start, energy=c.energy, win=c.win, blocker=c.blocker,
            focus_next=c.focus_next, values=values.get(c.id, {}),
        )
        for c in await rows(WeekCheck, WeekCheck.week_start, WeekCheck.id)
    ]
    return Backup.model_validate(
        {
            "version": 1,
            "profile": ProfileOut.model_validate(await get_profile(s)),
            "clients": await rows(Client, Client.name, Client.id),
            "projects": await rows(Project, Project.position, Project.id),
            "notes": await rows(Note, Note.date, Note.created_at, Note.id),
            "tasks": await rows(Task, Task.position, Task.created_at, Task.id),
            "entries": await rows(Entry, Entry.date, Entry.id),
            "recurring": await rows(Recurring, Recurring.start, Recurring.id),
            "paths": await rows(LearningPath, LearningPath.kind, LearningPath.created_at, LearningPath.id),
            "milestones": await rows(Milestone, Milestone.created_at, Milestone.id),
            "learning_items": await rows(LearningItem, LearningItem.created_at.desc(), LearningItem.id),
            "trips": await rows(Trip, Trip.start.is_(None), Trip.start, Trip.destination, Trip.id),
            "trip_items": await rows(TripItem, TripItem.created_at, TripItem.id),
            "goals": await rows(Goal, Goal.deadline, Goal.title, Goal.id),
            "metrics": await rows(Metric, Metric.created_at, Metric.id),
            "week_checks": checks,
            "accounts": await rows(Account, Account.created_at, Account.id),
            "balances": await rows(BalanceSnapshot, BalanceSnapshot.date, BalanceSnapshot.account_id),
            "funds": await rows(Fund, Fund.created_at, Fund.id),
            "fund_contributions": await rows(FundContribution, FundContribution.created_at, FundContribution.id),
        },
        from_attributes=True,
    )


def _check_references(b: Backup) -> None:
    clients = {c.id for c in b.clients}
    projects = {p.id for p in b.projects}
    paths = {p.id for p in b.paths}
    trips = {t.id for t in b.trips}
    metrics = {m.id for m in b.metrics}
    accounts = {a.id for a in b.accounts}
    funds = {f.id for f in b.funds}
    problems = [
        *(f"project {p.id}: unknown client" for p in b.projects if p.client_id and p.client_id not in clients),
        *(f"note {n.id}: unknown project" for n in b.notes if n.project_id not in projects),
        *(f"task {t.id}: unknown client" for t in b.tasks if t.client_id and t.client_id not in clients),
        *(f"task {t.id}: unknown project" for t in b.tasks if t.project_id and t.project_id not in projects),
        *(f"entry {e.id}: unknown project" for e in b.entries if e.project_id and e.project_id not in projects),
        *(f"recurring {r.id}: unknown project" for r in b.recurring if r.project_id and r.project_id not in projects),
        *(f"milestone {m.id}: unknown path" for m in b.milestones if m.path_id not in paths),
        *(f"item {i.id}: unknown path" for i in b.learning_items if i.path_id and i.path_id not in paths),
        *(f"trip item {i.id}: unknown trip" for i in b.trip_items if i.trip_id not in trips),
        *(f"week {w.id}: unknown metric" for w in b.week_checks for m in w.values if m not in metrics),
        *(f"balance {x.id}: unknown account" for x in b.balances if x.account_id not in accounts),
        *(f"fund {f.id}: unknown trip" for f in b.funds if f.trip_id and f.trip_id not in trips),
        *(f"contribution {c.id}: unknown fund" for c in b.fund_contributions if c.fund_id not in funds),
        *(f"entry {e.id}: unknown fund" for e in b.entries if e.fund_id and e.fund_id not in funds),
        *(f"recurring {r.id}: unknown fund" for r in b.recurring if r.fund_id and r.fund_id not in funds),
    ]
    if problems:
        raise InvalidError("; ".join(problems[:5]))


async def import_all(s: AsyncSession, b: Backup) -> None:
    """Replace everything atomically: any failure rolls back and leaves current data intact."""
    _check_references(b)
    try:
        for model in _WIPE_ORDER:
            await s.execute(delete(model))
        s.expunge_all()  # bulk deletes bypass the identity map
        profile = await get_profile(s)
        for key, value in b.profile.model_dump().items():
            setattr(profile, key, value)
        for model, items in (
            (Client, b.clients), (Project, b.projects), (Note, b.notes), (Task, b.tasks),
            (Trip, b.trips), (Fund, b.funds),  # entries and recurring items may point at a fund
            (Entry, b.entries), (Recurring, b.recurring),
            (LearningPath, b.paths), (Milestone, b.milestones), (LearningItem, b.learning_items),
            (TripItem, b.trip_items), (Goal, b.goals), (Metric, b.metrics),
            (Account, b.accounts), (BalanceSnapshot, b.balances), (FundContribution, b.fund_contributions),
        ):
            s.add_all(model(**i.model_dump()) for i in items)
            await s.flush()  # parents before children: no ORM relationships to order inserts
        for w in b.week_checks:
            s.add(WeekCheck(**w.model_dump(exclude={"values"})))
            await s.flush()
            s.add_all(WeekValue(check_id=w.id, metric_id=m, value=v) for m, v in w.values.items())
        await s.flush()
        await s.commit()
    except IntegrityError as exc:
        await s.rollback()
        raise InvalidError("backup violates database constraints") from exc
    except Exception:
        await s.rollback()
        raise
