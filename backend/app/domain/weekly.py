"""Weekly check rules: score, minimum viable week, burnout flag. Pure functions."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

TargetStatus = Literal["on_target", "close", "below"]
CLOSE_RATIO = Decimal("0.8")
BURNOUT_ENERGY = 2  # energy at or below this flags a deload

_ZERO, _ONE = Decimal(0), Decimal(1)


@dataclass(frozen=True, slots=True)
class MetricDef:
    id: UUID
    target: Decimal
    min_viable: Decimal | None


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_score(values: Mapping[UUID, Decimal], metrics: Sequence[MetricDef]) -> Decimal | None:
    """Mean of value/target (each capped at 1) over metrics that have a target and a logged value."""
    ratios = [min(values[m.id] / m.target, _ONE) for m in metrics if m.target > 0 and m.id in values]
    ratios = [max(r, _ZERO) for r in ratios]
    return sum(ratios, _ZERO) / len(ratios) if ratios else None


def is_min_viable(values: Mapping[UUID, Decimal], metrics: Sequence[MetricDef]) -> bool | None:
    """True when every metric with a minimum reached it. None when there is nothing to judge."""
    required = [m for m in metrics if m.min_viable is not None]
    if not required or not values:
        return None
    return all(m.id in values and values[m.id] >= m.min_viable for m in required)  # type: ignore[operator]


def burnout_risk(energy: int | None) -> bool:
    return energy is not None and energy <= BURNOUT_ENERGY


def metric_average(values: Sequence[Decimal]) -> Decimal | None:
    return sum(values, _ZERO) / len(values) if values else None


def target_status(average: Decimal | None, target: Decimal) -> TargetStatus | None:
    if average is None or target <= 0:
        return None
    if average >= target:
        return "on_target"
    return "close" if average >= CLOSE_RATIO * target else "below"
