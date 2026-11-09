from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Trip, TripItem
from app.domain.trips import budget_left, days_until, trip_cost
from app.schemas_life import TripDetail, TripItemOut, TripOut
from app.services import crud
from app.services.errors import InvalidError


def _summary(trip: Trip, items: list[TripItem], today: date) -> dict[str, Any]:
    spent = trip_cost(i.cost for i in items)
    return {
        "spent": spent,
        "budget_left": budget_left(trip.budget, spent),
        "days_until": days_until(trip.start, today),
        "items_total": len(items),
        "items_done": sum(i.done for i in items),
    }


async def list_trips(s: AsyncSession, today: date) -> list[TripOut]:
    trips = (await s.scalars(select(Trip).order_by(Trip.start.is_(None), Trip.start, Trip.destination))).all()
    by_trip: dict[uuid.UUID, list[TripItem]] = defaultdict(list)
    for it in (await s.scalars(select(TripItem))).all():
        by_trip[it.trip_id].append(it)
    return [TripOut.model_validate(t).model_copy(update=_summary(t, by_trip[t.id], today)) for t in trips]


async def trip_detail(s: AsyncSession, trip: Trip, today: date) -> TripDetail:
    items = await trip_items(s, trip.id)
    return TripDetail.model_validate(trip).model_copy(
        update={**_summary(trip, items, today), "items": [TripItemOut.model_validate(i) for i in items]}
    )


async def trip_items(s: AsyncSession, trip_id: uuid.UUID) -> list[TripItem]:
    stmt = select(TripItem).where(TripItem.trip_id == trip_id).order_by(TripItem.created_at, TripItem.id)
    return list((await s.scalars(stmt)).all())


async def update_trip(s: AsyncSession, trip: Trip, data: dict[str, Any]) -> Trip:
    start, end = data.get("start", trip.start), data.get("end", trip.end)
    if start and end and end < start:
        raise InvalidError("end must not be before start")
    return await crud.update(s, trip, data)
