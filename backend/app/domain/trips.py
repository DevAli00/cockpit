from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal


def trip_cost(costs: Iterable[Decimal | None]) -> Decimal:
    return sum((c for c in costs if c is not None), Decimal(0))


def budget_left(budget: Decimal | None, spent: Decimal) -> Decimal | None:
    return None if budget is None else budget - spent


def days_until(start: date | None, today: date) -> int | None:
    return None if start is None else (start - today).days
