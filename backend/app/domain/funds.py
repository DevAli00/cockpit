"""Savings funds (sinking funds): money earmarked for a purpose, with a target and maybe a deadline.

A fund is a label on money that sits in your accounts, not extra money: it does not change net worth.
"""
from __future__ import annotations

import calendar
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Literal
from uuid import UUID

from app.domain.finance import Txn

MovementSource = Literal["manual", "monthly", "income_share", "expense", "income"]
_IN_SOURCES = frozenset({"manual", "monthly", "income_share", "income"})

_ZERO, _ONE, _CENT = Decimal(0), Decimal(1), Decimal("0.01")


def fund_balance(movements: Iterable[Decimal]) -> Decimal:
    """Deposits are positive, withdrawals negative."""
    return sum(movements, _ZERO)


def fund_progress(balance: Decimal, target: Decimal) -> Decimal:
    return max(_ZERO, min(_ONE, balance / target)) if target > 0 else _ZERO


def _remaining(target: Decimal, balance: Decimal) -> Decimal:
    return max(_ZERO, target - balance)


def _ceil_cent(v: Decimal) -> Decimal:
    return v.quantize(_CENT, rounding=ROUND_CEILING)


def monthly_needed(target: Decimal, balance: Decimal, deadline: date | None, today: date) -> Decimal | None:
    """Per calendar month, counting this month and the deadline's month. None without a deadline."""
    left = _remaining(target, balance)
    if deadline is None:
        return None
    if left == 0:
        return _ZERO
    months = (deadline.year - today.year) * 12 + (deadline.month - today.month) + 1
    return _ceil_cent(left / max(1, months))


def weekly_needed(target: Decimal, balance: Decimal, deadline: date | None, today: date) -> Decimal | None:
    left = _remaining(target, balance)
    if deadline is None:
        return None
    if left == 0:
        return _ZERO
    weeks = max(1, math.ceil((deadline - today).days / 7))
    return _ceil_cent(left / weeks)


# --- automatic flows ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class FundRule:
    """How a fund fills itself: a fixed monthly amount and/or a share of every personal income."""

    fund_id: UUID
    start: date  # automation applies from this day on, never retroactively before it
    monthly_amount: Decimal | None
    monthly_day: int
    income_pct: Decimal | None


@dataclass(frozen=True, slots=True)
class Movement:
    fund_id: UUID
    date: date
    amount: Decimal  # positive = into the fund
    source: MovementSource
    label: str
    ref: str | None  # id of the contribution or transaction behind it, when there is one


def monthly_movements(rule: FundRule, today: date) -> list[Movement]:
    if not rule.monthly_amount or rule.monthly_amount <= 0:
        return []
    out = []
    y, m = rule.start.year, rule.start.month
    while (y, m) <= (today.year, today.month):
        day = date(y, m, min(rule.monthly_day, calendar.monthrange(y, m)[1]))
        if rule.start <= day <= today:
            out.append(Movement(rule.fund_id, day, rule.monthly_amount, "monthly", "Monthly saving", None))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _floor_cent(v: Decimal) -> Decimal:
    return v.quantize(_CENT, rounding=ROUND_FLOOR)


def income_share_movements(rule: FundRule, txns: Sequence[Txn], today: date) -> list[Movement]:
    """A share of each income since the rule started. Income already routed to a fund is skipped."""
    if not rule.income_pct or rule.income_pct <= 0:
        return []
    pct = rule.income_pct
    return [
        Movement(rule.fund_id, t.date, _floor_cent(t.amount * pct / 100), "income_share",
                 f"{pct.normalize():f}% of {t.label}", t.id)
        for t in txns
        if t.type == "revenue" and t.fund_id is None and rule.start <= t.date <= today
    ]


def linked_movements(txns: Sequence[Txn], fund_id: UUID) -> list[Movement]:
    """Expenses paid from the fund take money out; income routed into it adds money."""
    return [
        Movement(fund_id, t.date, t.amount if t.type == "revenue" else -t.amount,
                 "income" if t.type == "revenue" else "expense", t.label, t.id)
        for t in txns
        if t.fund_id == fund_id
    ]


def flow_totals(movements: Iterable[Movement], start: date | None, end: date) -> tuple[Decimal, Decimal]:
    """(money put into funds, money taken out of funds) within [start, end]."""
    into = out = _ZERO
    for mv in movements:
        if (start is not None and mv.date < start) or mv.date > end:
            continue
        if mv.amount > 0 and mv.source in _IN_SOURCES:
            into += mv.amount
        elif mv.amount < 0:
            out -= mv.amount
    return into, out
