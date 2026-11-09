"""Backup file format. Plain data only: derived fields (progress, spent…) are never stored."""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import (
    ClientOut, EntryOut, NoteOut, ProfileOut, ProjectOut, RecurringOut, TaskOut,
)
from app.schemas_money import AccountIn, BalanceOut, ContributionIn, FundIn
from app.schemas_life import (
    Amount, GoalIn, ItemIn, MetricIn, MilestoneIn, PathIn, TripIn, TripItemIn,
)


class _WithId(BaseModel):
    id: uuid.UUID


class _Stamped(_WithId):
    created_at: dt.datetime


class PathBackup(PathIn, _Stamped):
    pass


class MilestoneBackup(MilestoneIn, _Stamped):
    path_id: uuid.UUID


class ItemBackup(ItemIn, _Stamped):
    pass


class TripBackup(TripIn, _WithId):
    pass


class TripItemBackup(TripItemIn, _Stamped):
    trip_id: uuid.UUID


class GoalBackup(GoalIn, _WithId):
    pass


class MetricBackup(MetricIn, _Stamped):
    pass


class WeekCheckBackup(_WithId):
    week_start: dt.date
    energy: int | None
    win: str
    blocker: str
    focus_next: str
    values: dict[uuid.UUID, Amount] = Field(default_factory=dict)


class AccountBackup(AccountIn, _Stamped):
    pass


class FundBackup(FundIn, _Stamped):
    pass


class ContributionBackup(ContributionIn, _Stamped):
    fund_id: uuid.UUID


class Backup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1]
    profile: ProfileOut
    clients: list[ClientOut]
    projects: list[ProjectOut]
    notes: list[NoteOut]
    tasks: list[TaskOut]
    entries: list[EntryOut]
    recurring: list[RecurringOut]
    # Added later: older backup files simply do not have these keys.
    paths: list[PathBackup] = Field(default_factory=list)
    milestones: list[MilestoneBackup] = Field(default_factory=list)
    learning_items: list[ItemBackup] = Field(default_factory=list)
    trips: list[TripBackup] = Field(default_factory=list)
    trip_items: list[TripItemBackup] = Field(default_factory=list)
    goals: list[GoalBackup] = Field(default_factory=list)
    metrics: list[MetricBackup] = Field(default_factory=list)
    week_checks: list[WeekCheckBackup] = Field(default_factory=list)
    accounts: list[AccountBackup] = Field(default_factory=list)
    balances: list[BalanceOut] = Field(default_factory=list)
    funds: list[FundBackup] = Field(default_factory=list)
    fund_contributions: list[ContributionBackup] = Field(default_factory=list)


_ = Decimal  # re-exported types keep pydantic forward refs resolvable
