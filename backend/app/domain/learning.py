"""Learning rules: item progress, milestone completion, overdue detection."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Literal

ItemStatus = Literal["backlog", "in_progress", "done", "dropped"]
MilestoneStatus = Literal["todo", "doing", "done", "slipped"]


def item_percent(current: int, total: int | None) -> int | None:
    if not total or total <= 0:
        return None
    return max(0, min(100, round(current * 100 / total)))


def next_item_status(status: ItemStatus, current: int, total: int | None) -> ItemStatus:
    """Progress moves an item along, but a 'dropped' item stays dropped until you say otherwise."""
    if status == "dropped":
        return status
    if total and current >= total:
        return "done"
    if current > 0 and status == "backlog":
        return "in_progress"
    return status


def path_progress(statuses: Sequence[MilestoneStatus]) -> Decimal:
    if not statuses:
        return Decimal(0)
    return Decimal(sum(s == "done" for s in statuses)) / Decimal(len(statuses))


def is_overdue(status: MilestoneStatus, due: date | None, today: date) -> bool:
    return status != "done" and due is not None and due < today
