"""Pure task-board rules. Positions are floats so a move only rewrites the moved card."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

TaskColumn = Literal["todo", "ongoing", "blocked", "done"]

DONE_VISIBLE_FOR = timedelta(days=7)
REBALANCE_GAP = 1e-6


def position_between(prev: float | None, nxt: float | None) -> float:
    if prev is not None and nxt is not None:
        if prev >= nxt:
            raise ValueError("neighbours out of order")
        return (prev + nxt) / 2
    if nxt is not None:
        return nxt - 1
    if prev is not None:
        return prev + 1
    return 1.0


def needs_rebalance(prev: float | None, nxt: float | None) -> bool:
    """True when repeated halving left no usable room between two neighbours."""
    return prev is not None and nxt is not None and (nxt - prev) < REBALANCE_GAP


def done_at_for_move(
    old: TaskColumn, new: TaskColumn, done_at: datetime | None, now: datetime
) -> datetime | None:
    if new == "done" and old != "done":
        return now
    if new != "done":
        return None
    return done_at


def is_visible_on_board(col: TaskColumn, done_at: datetime | None, now: datetime) -> bool:
    """Done cards leave the board after a week (they stay stored)."""
    if col != "done" or done_at is None:
        return True
    return now - done_at <= DONE_VISIBLE_FOR
