from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Metric, WeekCheck, WeekValue
from app.domain.weekly import (
    MetricDef, burnout_risk, is_min_viable, metric_average, target_status, week_score, week_start,
)
from app.schemas_life import MetricSummary, WeekCheckIn, WeekCheckOut, WeeklySummary
from app.services import crud
from app.services.errors import InvalidError

_CENT = Decimal("0.01")


def _defs(metrics: list[Metric]) -> list[MetricDef]:
    return [MetricDef(m.id, m.target, m.min_viable) for m in metrics]


async def list_metrics(s: AsyncSession) -> list[Metric]:
    return await crud.list_all(s, Metric, Metric.created_at, Metric.id)


async def _values_by_check(s: AsyncSession) -> dict[uuid.UUID, dict[uuid.UUID, Decimal]]:
    out: dict[uuid.UUID, dict[uuid.UUID, Decimal]] = defaultdict(dict)
    for v in (await s.scalars(select(WeekValue))).all():
        out[v.check_id][v.metric_id] = v.value
    return out


def _check_out(c: WeekCheck, values: dict[uuid.UUID, Decimal], metrics: list[Metric]) -> WeekCheckOut:
    score = week_score(values, _defs(metrics))
    return WeekCheckOut(
        id=c.id, week_start=c.week_start, energy=c.energy, win=c.win, blocker=c.blocker,
        focus_next=c.focus_next, values=values,
        score=float(score) if score is not None else None,
        min_viable=is_min_viable(values, _defs(metrics)),
        burnout=burnout_risk(c.energy),
    )


async def list_checks(s: AsyncSession) -> list[WeekCheckOut]:
    metrics, values = await list_metrics(s), await _values_by_check(s)
    checks = await crud.list_all(s, WeekCheck, WeekCheck.week_start.desc())
    return [_check_out(c, values.get(c.id, {}), metrics) for c in checks]


async def upsert_check(s: AsyncSession, monday, body: WeekCheckIn) -> WeekCheckOut:  # type: ignore[no-untyped-def]
    if week_start(monday) != monday:
        raise InvalidError("week must start on a Monday")
    metrics = await list_metrics(s)
    unknown = set(body.values) - {m.id for m in metrics}
    if unknown:
        raise InvalidError("unknown metric in values")

    fields: dict[str, Any] = body.model_dump(exclude={"values"})
    check = (await s.scalars(select(WeekCheck).where(WeekCheck.week_start == monday))).first()
    if check is None:
        check = WeekCheck(week_start=monday, **fields)
        s.add(check)
        await s.flush()
    else:
        for k, v in fields.items():
            setattr(check, k, v)
        await s.execute(delete(WeekValue).where(WeekValue.check_id == check.id))
    s.add_all(WeekValue(check_id=check.id, metric_id=m, value=v) for m, v in body.values.items())
    await s.commit()
    values = (await _values_by_check(s)).get(check.id, {})
    return _check_out(check, values, metrics)


async def summary(s: AsyncSession) -> WeeklySummary:
    metrics, values_by_check = await list_metrics(s), await _values_by_check(s)
    checks = await crud.list_all(s, WeekCheck, WeekCheck.week_start.desc())
    logged = [c for c in checks if values_by_check.get(c.id)]
    verdicts = [is_min_viable(values_by_check[c.id], _defs(metrics)) for c in logged]
    judged = [v for v in verdicts if v is not None]

    rows = []
    for m in metrics:
        vals = [values_by_check[c.id][m.id] for c in logged if m.id in values_by_check[c.id]]
        avg = metric_average(vals)
        rows.append(
            MetricSummary(
                metric_id=m.id, name=m.name, unit=m.unit, target=m.target,
                average=str(avg.quantize(_CENT)) if avg is not None else None,
                status=target_status(avg, m.target),
            )
        )
    return WeeklySummary(
        weeks_logged=len(logged),
        consistency=round(sum(judged) / len(judged), 4) if judged else None,
        metrics=rows,
        last=_check_out(checks[0], values_by_check.get(checks[0].id, {}), metrics) if checks else None,
    )
