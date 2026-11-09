from datetime import date
from decimal import Decimal

from app.domain.funds import fund_balance, fund_progress, monthly_needed, weekly_needed

D = Decimal


def test_balance_adds_deposits_and_subtracts_withdrawals() -> None:
    assert fund_balance([D(100), D(50), D(-30)]) == D(120)
    assert fund_balance([]) == 0


def test_progress_is_clamped() -> None:
    assert fund_progress(D(600), D(2400)) == D("0.25")
    assert fund_progress(D(3000), D(2400)) == 1
    assert fund_progress(D(10), D(0)) == 0


def test_monthly_needed_spreads_the_remainder_over_months_left() -> None:
    today = date(2026, 11, 1)
    # 1800 left, deadline end of Feb 2027 -> Nov, Dec, Jan, Feb = 4 months
    assert monthly_needed(D(2400), D(600), date(2027, 2, 28), today) == D(450)
    # deadline this month or already past: everything is due now
    assert monthly_needed(D(2400), D(600), date(2026, 11, 20), today) == D(1800)
    assert monthly_needed(D(2400), D(600), date(2026, 10, 1), today) == D(1800)


def test_nothing_needed_when_funded_or_no_deadline() -> None:
    today = date(2026, 11, 1)
    assert monthly_needed(D(2400), D(2500), date(2027, 2, 28), today) == 0
    assert monthly_needed(D(2400), D(100), None, today) is None


def test_weekly_needed_rounds_up_to_the_cent() -> None:
    today = date(2026, 11, 1)  # a Sunday
    # 1000 left over 3 weeks (deadline 22 Nov) -> 333.34 so you never fall short
    assert weekly_needed(D(1000), D(0), date(2026, 11, 22), today) == D("333.34")
    assert weekly_needed(D(1000), D(0), date(2026, 11, 3), today) == D(1000)
    assert weekly_needed(D(10), D(20), date(2026, 12, 3), today) == 0
    assert weekly_needed(D(10), D(0), None, today) is None
