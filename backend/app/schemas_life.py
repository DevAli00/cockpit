"""API contracts for learning, trips, goals and the weekly check."""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.goals import GoalStatus
from app.domain.learning import ItemStatus, MilestoneStatus
from app.domain.weekly import TargetStatus
from app.schemas import ORM, Patch, Text, Title

Day = dt.date
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Short = Annotated[str, StringConstraints(max_length=100)]
Unit = Annotated[str, StringConstraints(max_length=30)]
WebUrl = Annotated[str, StringConstraints(max_length=2000, pattern=r"^(https?://\S+)?$")]
Amount = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PositiveAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]

PathKind = Literal["main", "secondary"]
PathStatus = Literal["active", "paused", "done"]
Horizon = Literal["weekly", "monthly", "quarterly", "semester"]
ItemKind = Literal["book", "article", "course", "lab", "video", "paper", "writing", "other"]
TripStatus = Literal["idea", "planned", "booked", "done"]
TripItemKind = Literal["flight", "stay", "activity", "todo", "other"]


# --- learning ---------------------------------------------------------------------------------
class PathIn(BaseModel):
    name: Name
    kind: PathKind = "main"
    description: Text = ""
    status: PathStatus = "active"
    start: Day | None = None
    target_date: Day | None = None


class PathPatch(Patch):
    name: Name | None = None
    kind: PathKind | None = None
    description: Text | None = None
    status: PathStatus | None = None
    start: Day | None = None
    target_date: Day | None = None


class PathOut(PathIn, ORM):
    id: uuid.UUID
    milestones_total: int = 0
    milestones_done: int = 0
    progress: float = 0.0


class MilestoneIn(BaseModel):
    title: Title
    horizon: Horizon = "weekly"
    due: Day | None = None
    status: MilestoneStatus = "todo"
    notes: Text = ""


class MilestonePatch(Patch):
    title: Title | None = None
    horizon: Horizon | None = None
    due: Day | None = None
    status: MilestoneStatus | None = None
    notes: Text | None = None


class MilestoneOut(MilestoneIn, ORM):
    id: uuid.UUID
    path_id: uuid.UUID
    overdue: bool = False


class ItemIn(BaseModel):
    kind: ItemKind
    title: Title
    author: Short = ""
    url: WebUrl = ""
    path_id: uuid.UUID | None = None
    status: ItemStatus = "backlog"
    progress_current: Annotated[int, Field(ge=0, le=10_000_000)] = 0
    progress_total: Annotated[int, Field(gt=0, le=10_000_000)] | None = None
    rating: Annotated[int, Field(ge=1, le=5)] | None = None
    started: Day | None = None
    finished: Day | None = None
    notes: Text = ""


class ItemPatch(Patch):
    kind: ItemKind | None = None
    title: Title | None = None
    author: Short | None = None
    url: WebUrl | None = None
    path_id: uuid.UUID | None = None
    status: ItemStatus | None = None
    progress_current: Annotated[int, Field(ge=0, le=10_000_000)] | None = None
    progress_total: Annotated[int, Field(gt=0, le=10_000_000)] | None = None
    rating: Annotated[int, Field(ge=1, le=5)] | None = None
    started: Day | None = None
    finished: Day | None = None
    notes: Text | None = None


class ItemOut(ItemIn, ORM):
    id: uuid.UUID
    percent: int | None = None


class LearningOverview(BaseModel):
    done_by_kind: dict[str, int]
    done_this_year: int
    in_progress: int
    backlog: int


# --- trips ------------------------------------------------------------------------------------
class _TripDates(BaseModel):
    @model_validator(mode="after")
    def _order(self) -> _TripDates:
        s, e = getattr(self, "start", None), getattr(self, "end", None)
        if s and e and e < s:
            raise ValueError("end must not be before start")
        return self


class TripIn(_TripDates):
    destination: Name
    start: Day | None = None
    end: Day | None = None
    status: TripStatus = "idea"
    budget: Amount | None = None
    notes: Text = ""


class TripPatch(Patch, _TripDates):
    destination: Name | None = None
    start: Day | None = None
    end: Day | None = None
    status: TripStatus | None = None
    budget: Amount | None = None
    notes: Text | None = None


class TripItemIn(BaseModel):
    kind: TripItemKind = "todo"
    label: Title
    date: Day | None = None
    cost: Amount | None = None
    done: bool = False


class TripItemPatch(Patch):
    kind: TripItemKind | None = None
    label: Title | None = None
    date: Day | None = None
    cost: Amount | None = None
    done: bool | None = None


class TripItemOut(TripItemIn, ORM):
    id: uuid.UUID
    trip_id: uuid.UUID


class TripOut(TripIn, ORM):
    id: uuid.UUID
    spent: Decimal = Decimal(0)
    budget_left: Decimal | None = None
    days_until: int | None = None
    items_total: int = 0
    items_done: int = 0


class TripDetail(TripOut):
    items: list[TripItemOut] = []


# --- goals ------------------------------------------------------------------------------------
class _GoalDates(BaseModel):
    @model_validator(mode="after")
    def _order(self) -> _GoalDates:
        s, e = getattr(self, "start", None), getattr(self, "deadline", None)
        if s and e and e <= s:
            raise ValueError("deadline must be after start")
        return self


class GoalIn(_GoalDates):
    title: Title
    area: Short = ""
    unit: Unit = ""
    target: PositiveAmount
    current: Amount = Decimal(0)
    start: Day
    deadline: Day


class GoalPatch(Patch, _GoalDates):
    title: Title | None = None
    area: Short | None = None
    unit: Unit | None = None
    target: PositiveAmount | None = None
    current: Amount | None = None
    start: Day | None = None
    deadline: Day | None = None


class GoalOut(GoalIn, ORM):
    id: uuid.UUID
    progress: float = 0.0
    expected: float = 0.0
    status: GoalStatus = "starting"


# --- weekly check -----------------------------------------------------------------------------
class MetricIn(BaseModel):
    name: Name
    unit: Unit = ""
    target: PositiveAmount
    min_viable: Amount | None = None


class MetricPatch(Patch):
    name: Name | None = None
    unit: Unit | None = None
    target: PositiveAmount | None = None
    min_viable: Amount | None = None


class MetricOut(MetricIn, ORM):
    id: uuid.UUID


class WeekCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    energy: Annotated[int, Field(ge=1, le=5)] | None = None
    win: Text = ""
    blocker: Text = ""
    focus_next: Text = ""
    values: dict[uuid.UUID, Amount] = Field(default_factory=dict)


class WeekCheckOut(BaseModel):
    id: uuid.UUID
    week_start: Day
    energy: int | None
    win: str
    blocker: str
    focus_next: str
    values: dict[uuid.UUID, Decimal]
    score: float | None
    min_viable: bool | None
    burnout: bool


class MetricSummary(BaseModel):
    metric_id: uuid.UUID
    name: str
    unit: str
    target: Decimal
    average: str | None
    status: TargetStatus | None


class WeeklySummary(BaseModel):
    weeks_logged: int
    consistency: float | None
    metrics: list[MetricSummary]
    last: WeekCheckOut | None
