from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.finance import (
    RecurringItem,
    Txn,
    expand_recurring,
    is_active,
    period_start,
    totals,
)


def rec(**kw) -> RecurringItem:
    base = dict(
        id=uuid4(), label="Hosting", type="opex", category="Software & SaaS",
        amount=Decimal("10"), frequency="monthly", start=date(2026, 1, 15),
        end=None, project_id=None,
    )
    return RecurringItem(**{**base, **kw})


def test_monthly_generates_one_txn_per_month_up_to_today() -> None:
    out = expand_recurring([rec()], today=date(2026, 3, 20))
    assert [t.date for t in out] == [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)]


def test_future_billing_day_is_not_counted() -> None:
    out = expand_recurring([rec()], today=date(2026, 3, 10))
    assert [t.date for t in out] == [date(2026, 1, 15), date(2026, 2, 15)]


def test_day_is_clamped_to_short_months() -> None:
    out = expand_recurring([rec(start=date(2026, 1, 31))], today=date(2026, 3, 31))
    assert [t.date for t in out] == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]


def test_end_date_is_inclusive_and_stops_generation() -> None:
    out = expand_recurring([rec(end=date(2026, 2, 15))], today=date(2026, 6, 1))
    assert [t.date for t in out] == [date(2026, 1, 15), date(2026, 2, 15)]


def test_yearly_only_in_anniversary_month() -> None:
    out = expand_recurring(
        [rec(frequency="yearly", start=date(2024, 5, 2))], today=date(2026, 12, 31)
    )
    assert [t.date for t in out] == [date(2024, 5, 2), date(2025, 5, 2), date(2026, 5, 2)]


def test_zero_amount_and_future_start_generate_nothing() -> None:
    assert expand_recurring([rec(amount=Decimal("0"))], today=date(2026, 3, 1)) == []
    assert expand_recurring([rec(start=date(2027, 1, 1))], today=date(2026, 3, 1)) == []


def test_generated_ids_are_stable_and_unique() -> None:
    item = rec()
    a = expand_recurring([item], today=date(2026, 3, 20))
    b = expand_recurring([item], today=date(2026, 3, 20))
    assert [t.id for t in a] == [t.id for t in b]
    assert len({t.id for t in a}) == 3
    assert all(t.recurring_id == item.id for t in a)


def test_is_active() -> None:
    today = date(2026, 3, 1)
    assert is_active(rec(), today)
    assert not is_active(rec(end=date(2026, 3, 1)), today)
    assert not is_active(rec(start=date(2026, 3, 2)), today)


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        ("month", date(2026, 3, 1)),
        ("3m", date(2026, 1, 1)),
        ("12m", date(2025, 4, 1)),
        ("all", None),
    ],
)
def test_period_start(period: str, expected: date | None) -> None:
    assert period_start(period, today=date(2026, 3, 20)) == expected  # type: ignore[arg-type]


def test_period_start_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        period_start("week", today=date(2026, 3, 20))  # type: ignore[arg-type]


def txn(type_: str, amount: str) -> Txn:
    return Txn(
        id=str(uuid4()), date=date(2026, 3, 1), label="x", type=type_,  # type: ignore[arg-type]
        category="c", amount=Decimal(amount), project_id=None, recurring_id=None,
    )


def test_totals_margin() -> None:
    t = totals([txn("revenue", "1000"), txn("direct", "200"), txn("opex", "300")])
    assert (t.revenue, t.direct, t.opex) == (Decimal("1000"), Decimal("200"), Decimal("300"))
    assert t.gross == Decimal("800")
    assert t.net == Decimal("500")
    assert t.gross_rate == Decimal("80")
    assert t.net_rate == Decimal("50")


def test_totals_empty_has_zero_rates_not_division_error() -> None:
    t = totals([])
    assert t.net == 0 and t.gross_rate == 0 and t.net_rate == 0
