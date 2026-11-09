"""North Star goals: progress against a target, judged against a linear expected pace."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

GoalStatus = Literal["done", "starting", "on_track", "behind"]

STARTING_GRACE = timedelta(days=7)  # no verdict during the first week
ON_TRACK_MARGIN = Decimal("0.1")  # may trail the expected pace by 10 points

_ZERO, _ONE = Decimal(0), Decimal(1)


def _clamp(v: Decimal) -> Decimal:
    return max(_ZERO, min(_ONE, v))


def progress(current: Decimal, target: Decimal) -> Decimal:
    return _clamp(current / target) if target > 0 else _ZERO


def expected_progress(start: date, deadline: date, today: date) -> Decimal:
    """Share of the time window elapsed (0..1). A zero or inverted window is 'due' as soon as reached."""
    total = (deadline - start).days
    if total <= 0:
        return _ONE if today >= deadline else _ZERO
    return _clamp(Decimal((today - start).days) / Decimal(total))


def goal_status(current: Decimal, target: Decimal, start: date, deadline: date, today: date) -> GoalStatus:
    done = progress(current, target)
    if done >= _ONE:
        return "done"
    if today < start + STARTING_GRACE:
        return "starting"
    return "on_track" if done >= expected_progress(start, deadline, today) - ON_TRACK_MARGIN else "behind"
