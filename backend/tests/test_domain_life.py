from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.goals import expected_progress, goal_status, progress
from app.domain.learning import is_overdue, item_percent, next_item_status, path_progress
from app.domain.trips import budget_left, days_until, trip_cost
from app.domain.weekly import (
    MetricDef, burnout_risk, is_min_viable, metric_average, target_status, week_score, week_start,
)

D = Decimal


# --- goals -------------------------------------------------------------------------------------
def test_progress_is_clamped_and_safe_on_zero_target() -> None:
    assert progress(D(5), D(10)) == D("0.5")
    assert progress(D(15), D(10)) == 1
    assert progress(D(-3), D(10)) == 0
    assert progress(D(5), D(0)) == 0


def test_expected_progress_is_linear_between_start_and_deadline() -> None:
    s, e = date(2026, 9, 21), date(2027, 3, 28)
    assert expected_progress(s, e, date(2026, 9, 1)) == 0
    assert expected_progress(s, e, date(2027, 6, 1)) == 1
    mid = expected_progress(s, e, date(2026, 12, 24))
    assert D("0.45") < mid < D("0.55")


def test_expected_progress_degenerate_range() -> None:
    d = date(2026, 1, 1)
    assert expected_progress(d, d, d) == 1
    assert expected_progress(d, date(2025, 1, 1), date(2025, 6, 1)) == 1


def test_goal_status_rules() -> None:
    s, e = date(2026, 9, 21), date(2027, 3, 28)
    assert goal_status(D(10), D(10), s, e, date(2026, 10, 1)) == "done"
    assert goal_status(D(0), D(10), s, e, date(2026, 9, 25)) == "starting"
    assert goal_status(D(5), D(10), s, e, date(2026, 12, 24)) == "on_track"
    assert goal_status(D(1), D(10), s, e, date(2026, 12, 24)) == "behind"
    # within the 10-point grace margin still counts as on track
    assert goal_status(D("4.1"), D(10), s, e, date(2026, 12, 24)) == "on_track"


# --- weekly ------------------------------------------------------------------------------------
def metrics() -> tuple[list[MetricDef], dict]:
    a, b = uuid4(), uuid4()
    return [MetricDef(a, D(16), D(5)), MetricDef(b, D(5), D(2))], {"a": a, "b": b}


def test_week_score_averages_capped_ratios() -> None:
    ms, k = metrics()
    assert week_score({k["a"]: D(8), k["b"]: D(5)}, ms) == D("0.75")
    assert week_score({k["a"]: D(32), k["b"]: D(5)}, ms) == 1  # over-achieving is capped
    assert week_score({k["a"]: D(8)}, ms) == D("0.5")  # only logged metrics count
    assert week_score({}, ms) is None


def test_week_score_ignores_metrics_without_target() -> None:
    m = MetricDef(uuid4(), D(0), None)
    assert week_score({m.id: D(3)}, [m]) is None


def test_min_viable() -> None:
    ms, k = metrics()
    assert is_min_viable({k["a"]: D(5), k["b"]: D(2)}, ms) is True
    assert is_min_viable({k["a"]: D(4), k["b"]: D(2)}, ms) is False
    assert is_min_viable({k["a"]: D(9)}, ms) is False  # a required metric is missing
    assert is_min_viable({}, ms) is None
    assert is_min_viable({k["a"]: D(1)}, [MetricDef(k["a"], D(5), None)]) is None


def test_burnout_and_status_and_average() -> None:
    assert burnout_risk(2) and burnout_risk(1)
    assert not burnout_risk(3) and not burnout_risk(None)
    assert target_status(D(16), D(16)) == "on_target"
    assert target_status(D(13), D(16)) == "close"
    assert target_status(D(5), D(16)) == "below"
    assert target_status(None, D(16)) is None
    assert metric_average([D(10), D(20)]) == 15
    assert metric_average([]) is None


def test_week_start_is_monday() -> None:
    assert week_start(date(2026, 10, 4)) == date(2026, 9, 28)  # Sunday -> Monday before
    assert week_start(date(2026, 9, 28)) == date(2026, 9, 28)


# --- learning ----------------------------------------------------------------------------------
def test_item_percent() -> None:
    assert item_percent(50, 200) == 25
    assert item_percent(300, 200) == 100
    assert item_percent(5, None) is None
    assert item_percent(5, 0) is None


@pytest.mark.parametrize(
    ("status", "cur", "tot", "expected"),
    [
        ("backlog", 10, 100, "in_progress"),
        ("in_progress", 100, 100, "done"),
        ("backlog", 0, 100, "backlog"),
        ("dropped", 50, 100, "dropped"),  # an explicit decision is never overridden by progress
        ("done", 100, 100, "done"),
        ("in_progress", 10, None, "in_progress"),
    ],
)
def test_next_item_status(status: str, cur: int, tot: int | None, expected: str) -> None:
    assert next_item_status(status, cur, tot) == expected  # type: ignore[arg-type]


def test_path_progress_and_overdue() -> None:
    assert path_progress(["done", "todo", "doing", "done"]) == D("0.5")
    assert path_progress([]) == 0
    today = date(2026, 10, 10)
    assert is_overdue("todo", date(2026, 10, 9), today)
    assert not is_overdue("done", date(2026, 10, 9), today)
    assert not is_overdue("todo", date(2026, 10, 10), today)
    assert not is_overdue("todo", None, today)


# --- trips -------------------------------------------------------------------------------------
def test_trip_money_and_countdown() -> None:
    assert trip_cost([D(100), None, D("50.5")]) == D("150.5")
    assert trip_cost([]) == 0
    assert budget_left(D(1000), D(250)) == 750
    assert budget_left(None, D(250)) is None
    assert days_until(date(2026, 12, 21), date(2026, 12, 1)) == 20
    assert days_until(date(2026, 11, 1), date(2026, 12, 1)) == -30
    assert days_until(None, date(2026, 12, 1)) is None
