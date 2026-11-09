"""Pure finance rules. No framework or database imports."""
from __future__ import annotations

import calendar
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

EntryType = Literal["revenue", "direct", "opex"]
Frequency = Literal["monthly", "yearly"]
Period = Literal["month", "3m", "12m", "all"]

_PERIOD_MONTHS: dict[str, int] = {"month": 1, "3m": 3, "12m": 12}
_HUNDRED = Decimal(100)
_RATE_STEP = Decimal("0.1")


@dataclass(frozen=True, slots=True)
class RecurringItem:
    id: UUID
    label: str
    type: EntryType
    category: str
    amount: Decimal
    frequency: Frequency
    start: date
    end: date | None
    project_id: UUID | None
    fund_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Txn:
    """A transaction as the finance views see it: typed in, or generated from a recurring item."""

    id: str
    date: date
    label: str
    type: EntryType
    category: str
    amount: Decimal
    project_id: UUID | None
    recurring_id: UUID | None
    fund_id: UUID | None = None  # personal money paid from / paid into a savings fund


@dataclass(frozen=True, slots=True)
class Totals:
    revenue: Decimal
    direct: Decimal
    opex: Decimal
    gross: Decimal
    net: Decimal
    gross_rate: Decimal
    net_rate: Decimal


def _months(start: date, last: date) -> Iterable[tuple[int, int]]:
    y, m = start.year, start.month
    while (y, m) <= (last.year, last.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def expand_recurring(items: Sequence[RecurringItem], today: date) -> list[Txn]:
    """One transaction per billing date, from start to end (inclusive) or today.

    Nothing is generated in the future: a charge only counts once its billing day has passed.
    The billing day is clamped to the month length (31st -> 28th in February).
    """
    out: list[Txn] = []
    for r in items:
        if not r.amount or r.start > today:
            continue
        for y, m in _months(r.start, today):
            if r.frequency == "yearly" and m != r.start.month:
                continue
            day = min(r.start.day, calendar.monthrange(y, m)[1])
            billed = date(y, m, day)
            if billed > today or (r.end is not None and billed > r.end):
                break
            out.append(
                Txn(
                    id=f"{r.id}:{y:04d}-{m:02d}", date=billed, label=r.label, type=r.type,
                    category=r.category, amount=r.amount, project_id=r.project_id,
                    recurring_id=r.id, fund_id=r.fund_id,
                )
            )
    return out


def is_active(r: RecurringItem, today: date) -> bool:
    return r.start <= today and (r.end is None or r.end > today)


def period_start(period: Period, today: date) -> date | None:
    """First day of the window, or None for 'all'. Windows are whole calendar months."""
    if period == "all":
        return None
    months = _PERIOD_MONTHS.get(period)
    if months is None:
        raise ValueError(f"unknown period: {period!r}")
    idx = today.year * 12 + (today.month - 1) - (months - 1)
    return date(idx // 12, idx % 12 + 1, 1)


def _sum(txns: Iterable[Txn], type_: EntryType) -> Decimal:
    return sum((t.amount for t in txns if t.type == type_), Decimal(0))


def _rate(part: Decimal, whole: Decimal) -> Decimal:
    return (part / whole * _HUNDRED).quantize(_RATE_STEP) if whole else Decimal(0)


def totals(txns: Sequence[Txn]) -> Totals:
    revenue, direct, opex = (_sum(txns, k) for k in ("revenue", "direct", "opex"))
    gross, net = revenue - direct, revenue - direct - opex
    return Totals(
        revenue=revenue, direct=direct, opex=opex, gross=gross, net=net,
        gross_rate=_rate(gross, revenue), net_rate=_rate(net, revenue),
    )
