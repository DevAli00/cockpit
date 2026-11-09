"""Net worth rules. Balances are point-in-time snapshots; the latest one on or before a date counts.

Every amount is a positive figure for what the account holds (assets) or what you owe (liabilities);
liabilities are subtracted. A cash account can still go negative when overdrawn.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

AccountType = Literal[
    "cash", "savings", "investment", "retirement", "crypto", "property", "vehicle", "other_asset",
    "loan", "mortgage", "credit_card", "other_debt",
]
LIABILITY_TYPES: frozenset[str] = frozenset({"loan", "mortgage", "credit_card", "other_debt"})
_ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class Account:
    id: UUID
    type: AccountType


@dataclass(frozen=True, slots=True)
class Snapshot:
    account_id: UUID
    at: date
    balance: Decimal


@dataclass(frozen=True, slots=True)
class NetWorth:
    assets: Decimal
    liabilities: Decimal
    net: Decimal


@dataclass(frozen=True, slots=True)
class HistoryPoint:
    at: date
    assets: Decimal
    liabilities: Decimal
    net: Decimal


def is_liability(t: AccountType) -> bool:
    return t in LIABILITY_TYPES


def latest_balances(snaps: Iterable[Snapshot], at: date) -> dict[UUID, Decimal]:
    best: dict[UUID, Snapshot] = {}
    for s in snaps:
        if s.at <= at and (s.account_id not in best or s.at > best[s.account_id].at):
            best[s.account_id] = s
    return {k: v.balance for k, v in best.items()}


def net_worth(accounts: Sequence[Account], balances: Mapping[UUID, Decimal]) -> NetWorth:
    assets = sum((balances[a.id] for a in accounts if a.id in balances and not is_liability(a.type)), _ZERO)
    debts = sum((balances[a.id] for a in accounts if a.id in balances and is_liability(a.type)), _ZERO)
    return NetWorth(assets=assets, liabilities=debts, net=assets - debts)


def allocation(accounts: Sequence[Account], balances: Mapping[UUID, Decimal]) -> list[tuple[str, Decimal]]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for a in accounts:
        if a.id in balances:
            totals[a.type] += balances[a.id]
    return sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))


def month_ends(first: date, today: date) -> list[date]:
    """Each month end from `first`'s month up to today; the current month ends at today."""
    out: list[date] = []
    y, m = first.year, first.month
    while (y, m) <= (today.year, today.month):
        end = date(y, m, calendar.monthrange(y, m)[1])
        out.append(min(end, today))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out if first <= today else []


def history(accounts: Sequence[Account], snaps: Sequence[Snapshot], today: date) -> list[HistoryPoint]:
    if not snaps:
        return []
    points = []
    for at in month_ends(min(s.at for s in snaps), today):
        t = net_worth(accounts, latest_balances(snaps, at))
        points.append(HistoryPoint(at=at, assets=t.assets, liabilities=t.liabilities, net=t.net))
    return points


def stale_accounts(
    accounts: Sequence[Account], snaps: Iterable[Snapshot], today: date, max_age_days: int
) -> set[UUID]:
    """Accounts never updated, or not updated within `max_age_days`."""
    last: dict[UUID, date] = {}
    for s in snaps:
        last[s.account_id] = max(last.get(s.account_id, s.at), s.at)
    limit = today - timedelta(days=max_age_days)
    return {a.id for a in accounts if a.id not in last or last[a.id] < limit}
