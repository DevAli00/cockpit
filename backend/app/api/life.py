"""Authenticated routes for learning, trips, goals and the weekly check."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.api.deps import Session, current_user
from app.domain.learning import ItemStatus
from app.db.models import Goal, LearningItem, LearningPath, Metric, Milestone, Trip, TripItem
from app.schemas_life import (
    GoalIn, GoalOut, GoalPatch, ItemIn, ItemOut, ItemPatch, LearningOverview, MetricIn, MetricOut,
    MetricPatch, MilestoneIn, MilestoneOut, MilestonePatch, PathIn, PathOut, PathPatch, TripDetail,
    TripIn, TripItemIn, TripItemOut, TripItemPatch, TripOut, TripPatch, WeekCheckIn, WeekCheckOut,
    WeeklySummary,
)
from app.schemas_life import Horizon, ItemKind
from app.services import crud, goals, learning, trips, weekly

router = APIRouter(dependencies=[Depends(current_user)])
NO_CONTENT = status.HTTP_204_NO_CONTENT


def _today() -> dt.date:
    return dt.date.today()


# --- learning: paths & milestones -------------------------------------------------------------
@router.get("/learning/paths", response_model=list[PathOut])
async def list_paths(s: Session) -> list[PathOut]:
    return await learning.list_paths(s)


@router.post("/learning/paths", response_model=PathOut, status_code=201)
async def create_path(body: PathIn, s: Session) -> PathOut:
    return await learning.path_out(s, await crud.create(s, LearningPath, body.model_dump()))


@router.patch("/learning/paths/{id}", response_model=PathOut)
async def patch_path(id: uuid.UUID, body: PathPatch, s: Session) -> PathOut:
    path = await crud.update(s, await crud.get_or_404(s, LearningPath, id), body.model_dump(exclude_unset=True))
    return await learning.path_out(s, path)


@router.delete("/learning/paths/{id}", status_code=NO_CONTENT)
async def delete_path(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, LearningPath, id))


@router.get("/learning/milestones", response_model=list[MilestoneOut])
async def list_milestones(
    s: Session, horizon: Horizon | None = None, path_id: uuid.UUID | None = None
) -> list[MilestoneOut]:
    return await learning.list_milestones(s, _today(), path_id=path_id, horizon=horizon)


@router.post("/learning/paths/{id}/milestones", response_model=MilestoneOut, status_code=201)
async def create_milestone(id: uuid.UUID, body: MilestoneIn, s: Session) -> MilestoneOut:
    await crud.get_or_404(s, LearningPath, id)
    m = await crud.create(s, Milestone, {**body.model_dump(), "path_id": id})
    return learning.milestone_out(m, _today())


@router.patch("/learning/milestones/{id}", response_model=MilestoneOut)
async def patch_milestone(id: uuid.UUID, body: MilestonePatch, s: Session) -> MilestoneOut:
    m = await crud.update(s, await crud.get_or_404(s, Milestone, id), body.model_dump(exclude_unset=True))
    return learning.milestone_out(m, _today())


@router.delete("/learning/milestones/{id}", status_code=NO_CONTENT)
async def delete_milestone(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Milestone, id))


# --- learning: library (books, articles, writing, labs…) --------------------------------------
@router.get("/learning/items", response_model=list[ItemOut])
async def list_items(
    s: Session, kind: ItemKind | None = None, status: ItemStatus | None = None, path_id: uuid.UUID | None = None
) -> list[ItemOut]:
    return [learning.item_out(i) for i in await learning.list_items(s, kind=kind, status=status, path_id=path_id)]


@router.post("/learning/items", response_model=ItemOut, status_code=201)
async def create_item(body: ItemIn, s: Session) -> ItemOut:
    return learning.item_out(await learning.create_item(s, body.model_dump(exclude_unset=True), _today()))


@router.patch("/learning/items/{id}", response_model=ItemOut)
async def patch_item(id: uuid.UUID, body: ItemPatch, s: Session) -> ItemOut:
    item = await crud.get_or_404(s, LearningItem, id)
    return learning.item_out(await learning.update_item(s, item, body.model_dump(exclude_unset=True), _today()))


@router.delete("/learning/items/{id}", status_code=NO_CONTENT)
async def delete_item(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, LearningItem, id))


@router.get("/learning/overview", response_model=LearningOverview)
async def learning_overview(s: Session) -> LearningOverview:
    return await learning.overview(s, _today())


# --- trips ------------------------------------------------------------------------------------
@router.get("/trips", response_model=list[TripOut])
async def list_trips(s: Session) -> list[TripOut]:
    return await trips.list_trips(s, _today())


@router.post("/trips", response_model=TripDetail, status_code=201)
async def create_trip(body: TripIn, s: Session) -> TripDetail:
    return await trips.trip_detail(s, await crud.create(s, Trip, body.model_dump()), _today())


@router.get("/trips/{id}", response_model=TripDetail)
async def get_trip(id: uuid.UUID, s: Session) -> TripDetail:
    return await trips.trip_detail(s, await crud.get_or_404(s, Trip, id), _today())


@router.patch("/trips/{id}", response_model=TripDetail)
async def patch_trip(id: uuid.UUID, body: TripPatch, s: Session) -> TripDetail:
    trip = await trips.update_trip(s, await crud.get_or_404(s, Trip, id), body.model_dump(exclude_unset=True))
    return await trips.trip_detail(s, trip, _today())


@router.delete("/trips/{id}", status_code=NO_CONTENT)
async def delete_trip(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Trip, id))


@router.post("/trips/{id}/items", response_model=TripItemOut, status_code=201)
async def create_trip_item(id: uuid.UUID, body: TripItemIn, s: Session) -> TripItem:
    await crud.get_or_404(s, Trip, id)
    return await crud.create(s, TripItem, {**body.model_dump(), "trip_id": id})


@router.patch("/trips/items/{id}", response_model=TripItemOut)
async def patch_trip_item(id: uuid.UUID, body: TripItemPatch, s: Session) -> TripItem:
    return await crud.update(s, await crud.get_or_404(s, TripItem, id), body.model_dump(exclude_unset=True))


@router.delete("/trips/items/{id}", status_code=NO_CONTENT)
async def delete_trip_item(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, TripItem, id))


# --- goals ------------------------------------------------------------------------------------
@router.get("/goals", response_model=list[GoalOut])
async def list_goals(s: Session) -> list[GoalOut]:
    rows = (await s.scalars(select(Goal).order_by(Goal.deadline, Goal.title))).all()
    return [goals.goal_out(g, _today()) for g in rows]


@router.post("/goals", response_model=GoalOut, status_code=201)
async def create_goal(body: GoalIn, s: Session) -> GoalOut:
    return goals.goal_out(await crud.create(s, Goal, body.model_dump()), _today())


@router.patch("/goals/{id}", response_model=GoalOut)
async def patch_goal(id: uuid.UUID, body: GoalPatch, s: Session) -> GoalOut:
    goal = await goals.update_goal(s, await crud.get_or_404(s, Goal, id), body.model_dump(exclude_unset=True))
    return goals.goal_out(goal, _today())


@router.delete("/goals/{id}", status_code=NO_CONTENT)
async def delete_goal(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Goal, id))


# --- weekly check -----------------------------------------------------------------------------
@router.get("/weekly/metrics", response_model=list[MetricOut])
async def list_metrics(s: Session) -> list[Metric]:
    return await weekly.list_metrics(s)


@router.post("/weekly/metrics", response_model=MetricOut, status_code=201)
async def create_metric(body: MetricIn, s: Session) -> Metric:
    return await crud.create(s, Metric, body.model_dump())


@router.patch("/weekly/metrics/{id}", response_model=MetricOut)
async def patch_metric(id: uuid.UUID, body: MetricPatch, s: Session) -> Metric:
    return await crud.update(s, await crud.get_or_404(s, Metric, id), body.model_dump(exclude_unset=True))


@router.delete("/weekly/metrics/{id}", status_code=NO_CONTENT)
async def delete_metric(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Metric, id))


@router.get("/weekly/checks", response_model=list[WeekCheckOut])
async def list_checks(s: Session) -> list[WeekCheckOut]:
    return await weekly.list_checks(s)


@router.put("/weekly/checks/{week_start}", response_model=WeekCheckOut)
async def put_check(week_start: dt.date, body: WeekCheckIn, s: Session) -> WeekCheckOut:
    return await weekly.upsert_check(s, week_start, body)


@router.get("/weekly/summary", response_model=WeeklySummary)
async def weekly_summary(s: Session) -> WeeklySummary:
    return await weekly.summary(s)

