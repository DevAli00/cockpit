from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Fund, FundContribution
from app.domain.finance import Txn
from app.domain.funds import (
    FundRule, Movement, flow_totals, fund_balance, fund_progress, income_share_movements, linked_movements,
    monthly_movements, monthly_needed, weekly_needed,
)
from app.schemas_money import ContributionIn, FundOut, MovementOut
from app.services import crud
from app.services.errors import InvalidError
from app.services.ledger import load_txns

_RULE_FIELDS = ("monthly_amount", "monthly_day", "income_pct")


def _rule(f: Fund) -> FundRule:
    return FundRule(
        fund_id=f.id, start=f.auto_start or f.created_at.date(),
        monthly_amount=f.monthly_amount, monthly_day=f.monthly_day, income_pct=f.income_pct,
    )


def _auto_movements(f: Fund, txns: list[Txn], today: date) -> list[Movement]:
    rule = _rule(f)
    return [*monthly_movements(rule, today), *income_share_movements(rule, txns, today)]


def _manual(c: FundContribution) -> Movement:
    label = c.note or ("Added" if c.amount > 0 else "Taken out")
    return Movement(c.fund_id, c.date, c.amount, "manual", label, str(c.id))


async def _context(s: AsyncSession, today: date) -> tuple[list[Txn], dict[uuid.UUID, list[FundContribution]]]:
    txns = await load_txns(s, today, "personal")
    by_fund: dict[uuid.UUID, list[FundContribution]] = defaultdict(list)
    for c in (await s.scalars(select(FundContribution))).all():
        by_fund[c.fund_id].append(c)
    return txns, by_fund


def _ledger(f: Fund, txns: list[Txn], contributions: list[FundContribution], today: date) -> list[Movement]:
    """Every movement of a fund: manual, automatic, and transactions linked to it."""
    moves = [*map(_manual, contributions), *_auto_movements(f, txns, today), *linked_movements(txns, f.id)]
    return sorted(moves, key=lambda m: (m.date, m.amount), reverse=True)


def _out(f: Fund, ledger: list[Movement], today: date) -> FundOut:
    bal = fund_balance(m.amount for m in ledger)
    return FundOut.model_validate(f).model_copy(
        update={
            "balance": bal,
            "remaining": max(Decimal(0), f.target - bal),
            "progress": float(fund_progress(bal, f.target)),
            "funded": bal >= f.target,
            "monthly_needed": monthly_needed(f.target, bal, f.deadline, today),
            "weekly_needed": weekly_needed(f.target, bal, f.deadline, today),
            "contributions": len(ledger),
        }
    )


async def list_funds(s: AsyncSession, today: date, trip_id: uuid.UUID | None = None) -> list[FundOut]:
    stmt = select(Fund).order_by(Fund.deadline.is_(None), Fund.deadline, Fund.created_at)
    if trip_id:
        stmt = stmt.where(Fund.trip_id == trip_id)
    funds = (await s.scalars(stmt)).all()
    txns, contribs = await _context(s, today)
    return [_out(f, _ledger(f, txns, contribs[f.id], today), today) for f in funds]


async def fund_out(s: AsyncSession, fund: Fund, today: date) -> FundOut:
    return next(f for f in await list_funds(s, today) if f.id == fund.id)


async def ledger(s: AsyncSession, fund: Fund, today: date) -> list[MovementOut]:
    txns, contribs = await _context(s, today)
    return [
        MovementOut(date=m.date, amount=m.amount, source=m.source, label=m.label, ref=m.ref)
        for m in _ledger(fund, txns, contribs[fund.id], today)
    ]


async def all_movements(s: AsyncSession, today: date) -> list[Movement]:
    funds = (await s.scalars(select(Fund))).all()
    txns, contribs = await _context(s, today)
    return [m for f in funds for m in _ledger(f, txns, contribs[f.id], today)]


async def period_flow(s: AsyncSession, start: date | None, today: date) -> tuple[Decimal, Decimal]:
    return flow_totals(await all_movements(s, today), start, today)


async def _balance(s: AsyncSession, fund: Fund, today: date) -> Decimal:
    txns, contribs = await _context(s, today)
    return fund_balance(m.amount for m in _ledger(fund, txns, contribs[fund.id], today))


async def _check_income_share(s: AsyncSession, pct: Decimal | None, exclude: uuid.UUID | None) -> None:
    if not pct:
        return
    stmt = select(Fund.income_pct).where(Fund.income_pct.is_not(None))
    if exclude:
        stmt = stmt.where(Fund.id != exclude)
    # Summed here, not in SQL: SQLite would add them as floats and 33.3+33.3+33.4 would exceed 100.
    if sum((await s.scalars(stmt)).all(), Decimal(0)) + pct > 100:
        raise InvalidError("funds cannot take more than 100% of income in total")


async def create_fund(s: AsyncSession, data: dict[str, Any], today: date) -> Fund:
    await _check_income_share(s, data.get("income_pct"), None)
    return await crud.create(s, Fund, {**data, "auto_start": data.get("auto_start") or today})


async def update_fund(s: AsyncSession, fund: Fund, data: dict[str, Any], today: date) -> Fund:
    if "income_pct" in data:
        await _check_income_share(s, data["income_pct"], fund.id)
    changed = any(k in data and data[k] != getattr(fund, k) for k in _RULE_FIELDS)
    start = fund.auto_start or fund.created_at.date()
    if changed and start < today:
        # A new rule must not rewrite history: freeze what the old rule produced before today.
        txns, _ = await _context(s, today)
        for m in _auto_movements(fund, txns, today):
            if m.date < today and m.amount != 0:
                s.add(FundContribution(fund_id=fund.id, date=m.date, amount=m.amount, note=f"{m.label} (auto)"))
        data = {**data, "auto_start": today}
    return await crud.update(s, fund, data)


async def add_contribution(s: AsyncSession, fund: Fund, body: ContributionIn, today: date) -> FundContribution:
    if body.amount == 0:
        raise InvalidError("amount must not be zero")
    if body.date > today:
        raise InvalidError("contributions cannot be dated in the future")
    if body.amount < 0 and await _balance(s, fund, today) + body.amount < 0:
        raise InvalidError("that withdrawal would take the fund below zero")
    return await crud.create(s, FundContribution, {**body.model_dump(), "fund_id": fund.id})


async def delete_contribution(s: AsyncSession, c: FundContribution, today: date) -> None:
    fund = await crud.get_or_404(s, Fund, c.fund_id)
    if c.amount > 0 and await _balance(s, fund, today) - c.amount < 0:
        raise InvalidError("removing this deposit would take the fund below zero: delete the withdrawal first")
    await crud.delete(s, c)


async def contributions(s: AsyncSession, fund_id: uuid.UUID) -> list[FundContribution]:
    stmt = (
        select(FundContribution).where(FundContribution.fund_id == fund_id)
        .order_by(FundContribution.date.desc(), FundContribution.created_at.desc())
    )
    return list((await s.scalars(stmt)).all())
