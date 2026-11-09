from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.networth import (
    Account, Snapshot, allocation, history, is_liability, latest_balances, month_ends, net_worth,
    stale_accounts,
)

D = Decimal


def acct(type_: str = "savings") -> Account:
    return Account(id=uuid4(), type=type_)  # type: ignore[arg-type]


@pytest.mark.parametrize("t", ["loan", "mortgage", "credit_card", "other_debt"])
def test_liability_types(t: str) -> None:
    assert is_liability(t)  # type: ignore[arg-type]


@pytest.mark.parametrize("t", ["cash", "savings", "investment", "retirement", "crypto", "property", "vehicle", "other_asset"])
def test_asset_types(t: str) -> None:
    assert not is_liability(t)  # type: ignore[arg-type]


def test_latest_balance_on_or_before_date_wins() -> None:
    a = acct()
    snaps = [
        Snapshot(a.id, date(2026, 1, 31), D(100)),
        Snapshot(a.id, date(2026, 3, 31), D(300)),
        Snapshot(a.id, date(2026, 2, 28), D(200)),  # unordered input
    ]
    assert latest_balances(snaps, date(2026, 3, 15)) == {a.id: D(200)}
    assert latest_balances(snaps, date(2026, 3, 31)) == {a.id: D(300)}
    assert latest_balances(snaps, date(2025, 12, 31)) == {}


def test_net_worth_subtracts_liabilities() -> None:
    cash, loan = acct("cash"), acct("loan")
    t = net_worth([cash, loan], {cash.id: D(5000), loan.id: D(1200)})
    assert (t.assets, t.liabilities, t.net) == (D(5000), D(1200), D(3800))


def test_net_worth_ignores_balances_of_unknown_accounts_and_missing_ones() -> None:
    cash = acct("cash")
    t = net_worth([cash, acct("savings")], {cash.id: D(10), uuid4(): D(999)})
    assert t.net == D(10)


def test_overdrawn_cash_lowers_assets() -> None:
    cash = acct("cash")
    assert net_worth([cash], {cash.id: D(-50)}).net == D(-50)


def test_allocation_groups_by_type_largest_first() -> None:
    a, b, c, l = acct("savings"), acct("savings"), acct("crypto"), acct("loan")
    out = allocation([a, b, c, l], {a.id: D(100), b.id: D(50), c.id: D(400), l.id: D(80)})
    assert out == [("crypto", D(400)), ("savings", D(150)), ("loan", D(80))]


def test_month_ends_runs_to_today() -> None:
    assert month_ends(date(2026, 1, 15), date(2026, 4, 10)) == [
        date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 10),
    ]
    assert month_ends(date(2026, 4, 2), date(2026, 4, 10)) == [date(2026, 4, 10)]
    assert month_ends(date(2026, 5, 1), date(2026, 4, 10)) == []


def test_history_carries_last_known_balance_forward() -> None:
    cash, loan = acct("cash"), acct("loan")
    snaps = [
        Snapshot(cash.id, date(2026, 1, 10), D(1000)),
        Snapshot(loan.id, date(2026, 1, 10), D(500)),
        Snapshot(cash.id, date(2026, 3, 5), D(1600)),
    ]
    h = history([cash, loan], snaps, date(2026, 3, 20))
    assert [(p.at, p.net) for p in h] == [
        (date(2026, 1, 31), D(500)), (date(2026, 2, 28), D(500)), (date(2026, 3, 20), D(1100)),
    ]
    assert history([cash], [], date(2026, 3, 20)) == []


def test_stale_accounts() -> None:
    fresh, old, never = acct(), acct(), acct()
    snaps = [Snapshot(fresh.id, date(2026, 3, 1), D(1)), Snapshot(old.id, date(2026, 1, 1), D(1))]
    assert stale_accounts([fresh, old, never], snaps, date(2026, 3, 20), max_age_days=45) == {old.id, never.id}
