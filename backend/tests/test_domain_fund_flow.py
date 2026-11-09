from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.finance import Txn
from app.domain.funds import (
    FundRule, flow_totals, income_share_movements, linked_movements, monthly_movements,
)

D = Decimal
F = uuid4()


def rule(**kw) -> FundRule:
    base = dict(fund_id=F, start=date(2026, 9, 15), monthly_amount=None, monthly_day=1, income_pct=None)
    return FundRule(**{**base, **kw})


def txn(type_: str, amount: str, day: date, fund_id=None, label: str = "x") -> Txn:
    return Txn(id=str(uuid4()), date=day, label=label, type=type_, category="c",  # type: ignore[arg-type]
               amount=D(amount), project_id=None, recurring_id=None, fund_id=fund_id)


def test_monthly_deposits_from_start_to_today() -> None:
    out = monthly_movements(rule(monthly_amount=D(200), monthly_day=1), today=date(2026, 11, 20))
    assert [(m.date, m.amount, m.source) for m in out] == [
        (date(2026, 10, 1), D(200), "monthly"), (date(2026, 11, 1), D(200), "monthly"),
    ]  # 1 Sept is before the rule started


def test_monthly_day_waits_for_its_day_and_is_off_without_amount() -> None:
    assert len(monthly_movements(rule(monthly_amount=D(50), monthly_day=25), today=date(2026, 11, 20))) == 2  # 25 Sep, 25 Oct
    assert monthly_movements(rule(), today=date(2026, 11, 20)) == []
    assert monthly_movements(rule(monthly_amount=D(0)), today=date(2026, 11, 20)) == []


def test_income_share_takes_a_percentage_of_each_income_after_start() -> None:
    incomes = [
        txn("revenue", "3000", date(2026, 10, 1), label="Salary"),
        txn("revenue", "1000", date(2026, 9, 1)),  # before start
        txn("opex", "500", date(2026, 10, 2)),  # not income
        txn("revenue", "999.99", date(2026, 10, 3)),
        txn("revenue", "100", date(2026, 10, 4), fund_id=uuid4()),  # already routed to a fund
        txn("revenue", "100", date(2026, 12, 1)),  # future
    ]
    out = income_share_movements(rule(income_pct=D(10)), incomes, today=date(2026, 11, 1))
    assert [(m.amount, m.label) for m in out] == [(D(300), "10% of Salary"), (D("99.99"), "10% of x")]  # floored to the cent
    assert income_share_movements(rule(), incomes, today=date(2026, 11, 1)) == []


def test_linked_transactions_move_their_fund() -> None:
    other = uuid4()
    out = linked_movements([
        txn("opex", "300", date(2026, 10, 5), fund_id=F, label="Flight"),
        txn("revenue", "150", date(2026, 10, 6), fund_id=F, label="Eid money"),
        txn("opex", "20", date(2026, 10, 7), fund_id=other),
        txn("opex", "99", date(2026, 10, 8)),
    ], fund_id=F)
    assert [(m.amount, m.source) for m in out] == [(D(-300), "expense"), (D(150), "income")]


def test_flow_totals_split_money_into_and_out_of_funds_within_a_window() -> None:
    from app.domain.funds import Movement

    mv = [
        Movement(F, date(2026, 10, 1), D(200), "monthly", "", None),
        Movement(F, date(2026, 10, 2), D(300), "income_share", "", None),
        Movement(F, date(2026, 10, 3), D(50), "manual", "", None),
        Movement(F, date(2026, 10, 4), D(-80), "manual", "", None),
        Movement(F, date(2026, 10, 5), D(-120), "expense", "", None),
        Movement(F, date(2026, 10, 6), D(40), "income", "", None),
        Movement(F, date(2026, 9, 30), D(999), "monthly", "", None),  # outside window
    ]
    to_funds, from_funds = flow_totals(mv, start=date(2026, 10, 1), end=date(2026, 10, 31))
    assert (to_funds, from_funds) == (D(590), D(200))
    assert flow_totals(mv, start=None, end=date(2026, 10, 31))[0] == D(1589)
