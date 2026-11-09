"""Loads transactions (typed-in entries + expanded recurring items) as domain Txns.

Shared by the finance summary and the funds, so both always see the same money.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Entry, Recurring
from app.domain.finance import RecurringItem, Txn, expand_recurring


async def load_txns(s: AsyncSession, today: date, scope: str, start: date | None = None) -> list[Txn]:
    """Everything that has happened by today for `scope` ('business', 'personal' or 'all')."""
    stmt = select(Entry).where(Entry.date <= today)  # planned (future) entries stay out
    rec_stmt = select(Recurring)
    if scope != "all":
        stmt = stmt.where(Entry.scope == scope)
        rec_stmt = rec_stmt.where(Recurring.scope == scope)
    if start is not None:
        stmt = stmt.where(Entry.date >= start)
    txns = [
        Txn(
            id=str(e.id), date=e.date, label=e.label, type=e.type, category=e.category,  # type: ignore[arg-type]
            amount=e.amount, project_id=e.project_id, recurring_id=None, fund_id=e.fund_id,
        )
        for e in (await s.scalars(stmt)).all()
    ]
    items = [
        RecurringItem(
            id=r.id, label=r.label, type=r.type, category=r.category, amount=r.amount,  # type: ignore[arg-type]
            frequency=r.frequency, start=r.start, end=r.end, project_id=r.project_id,  # type: ignore[arg-type]
            fund_id=r.fund_id,
        )
        for r in (await s.scalars(rec_stmt)).all()
    ]
    txns += [t for t in expand_recurring(items, today) if start is None or t.date >= start]
    return txns
