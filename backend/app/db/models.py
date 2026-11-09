from __future__ import annotations

import uuid
import datetime as dt
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON, CheckConstraint, Date, Float, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.expression import true

from app.db.base import Base
from app.db.types import UTCDateTime

Day = dt.date


def _now() -> datetime:
    return datetime.now(UTC)


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def _fk(table: str, *, cascade: bool = False) -> Mapped[uuid.UUID | None]:
    return mapped_column(
        Uuid, ForeignKey(f"{table}.id", ondelete="CASCADE" if cascade else "SET NULL"), index=True
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _pk()
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class Profile(Base):
    """Single-row settings table (id is always 1)."""

    __tablename__ = "profile"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    company: Mapped[str] = mapped_column(String(200), default="")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    show_business: Mapped[bool] = mapped_column(default=True, server_default=true())
    __table_args__ = (CheckConstraint("id = 1", name="profile_singleton"),)


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    color: Mapped[str] = mapped_column(String(7))


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    client_id: Mapped[uuid.UUID | None] = _fk("clients")
    start: Mapped[Day | None] = mapped_column(Date)
    deadline: Mapped[Day | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="Not started")
    position: Mapped[float] = mapped_column(Float, default=0.0)
    brief: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    __table_args__ = (
        CheckConstraint("status in ('Not started','In progress','On hold','Done')", name="project_status"),
    )


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[uuid.UUID] = _pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[Day] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(20), default="note")
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (
        CheckConstraint("kind in ('note','call','decision','feedback','email')", name="note_kind"),
    )


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = _pk()
    title: Mapped[str] = mapped_column(String(300))
    col: Mapped[str] = mapped_column(String(10), default="todo")
    client_id: Mapped[uuid.UUID | None] = _fk("clients")
    project_id: Mapped[uuid.UUID | None] = _fk("projects")
    due: Mapped[Day | None] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[float] = mapped_column(Float, default=1.0)
    done_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (
        CheckConstraint("col in ('todo','ongoing','blocked','done')", name="task_col"),
        Index("ix_tasks_col_position", "col", "position"),
    )


class Entry(Base):
    __tablename__ = "entries"
    id: Mapped[uuid.UUID] = _pk()
    date: Mapped[Day] = mapped_column(Date, index=True)
    label: Mapped[str] = mapped_column(String(300))
    type: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    project_id: Mapped[uuid.UUID | None] = _fk("projects")
    scope: Mapped[str] = mapped_column(String(10), default="business", server_default="business", index=True)
    fund_id: Mapped[uuid.UUID | None] = _fk("funds")
    __table_args__ = (
        CheckConstraint("type in ('revenue','direct','opex')", name="entry_type"),
        CheckConstraint("scope in ('business','personal')", name="entry_scope"),
        CheckConstraint("fund_id is null or scope = 'personal'", name="entry_fund_personal"),
        CheckConstraint("amount > 0", name="entry_amount_positive"),
    )


class Recurring(Base):
    __tablename__ = "recurring"
    id: Mapped[uuid.UUID] = _pk()
    label: Mapped[str] = mapped_column(String(300))
    type: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    frequency: Mapped[str] = mapped_column(String(10))
    start: Mapped[Day] = mapped_column(Date)
    end: Mapped[Day | None] = mapped_column(Date)
    project_id: Mapped[uuid.UUID | None] = _fk("projects")
    scope: Mapped[str] = mapped_column(String(10), default="business", server_default="business")
    fund_id: Mapped[uuid.UUID | None] = _fk("funds")
    __table_args__ = (
        CheckConstraint("type in ('revenue','direct','opex')", name="recurring_type"),
        CheckConstraint("scope in ('business','personal')", name="recurring_scope"),
        CheckConstraint("fund_id is null or scope = 'personal'", name="recurring_fund_personal"),
        CheckConstraint("frequency in ('monthly','yearly')", name="recurring_frequency"),
        CheckConstraint("amount > 0", name="recurring_amount_positive"),
    )


# --- life cockpit: learning, trips, goals, weekly check -------------------------------------
class LearningPath(Base):
    __tablename__ = "learning_paths"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10), default="main")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="active")
    start: Mapped[Day | None] = mapped_column(Date)
    target_date: Mapped[Day | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (
        CheckConstraint("kind in ('main','secondary')", name="path_kind"),
        CheckConstraint("status in ('active','paused','done')", name="path_status"),
    )


class Milestone(Base):
    __tablename__ = "milestones"
    id: Mapped[uuid.UUID] = _pk()
    path_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    horizon: Mapped[str] = mapped_column(String(10), default="weekly")
    due: Mapped[Day | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="todo")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (
        CheckConstraint("horizon in ('weekly','monthly','quarterly','semester')", name="milestone_horizon"),
        CheckConstraint("status in ('todo','doing','done','slipped')", name="milestone_status"),
    )


class LearningItem(Base):
    """A book, article, course, lab, video, paper or piece of writing."""

    __tablename__ = "learning_items"
    id: Mapped[uuid.UUID] = _pk()
    path_id: Mapped[uuid.UUID | None] = _fk("learning_paths")
    kind: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(300))
    author: Mapped[str] = mapped_column(String(200), default="")
    url: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(12), default="backlog")
    progress_current: Mapped[int] = mapped_column(default=0)
    progress_total: Mapped[int | None] = mapped_column()
    rating: Mapped[int | None] = mapped_column()
    started: Mapped[Day | None] = mapped_column(Date)
    finished: Mapped[Day | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (
        CheckConstraint(
            "kind in ('book','article','course','lab','video','paper','writing','other')", name="item_kind"
        ),
        CheckConstraint("status in ('backlog','in_progress','done','dropped')", name="item_status"),
        CheckConstraint("rating is null or (rating between 1 and 5)", name="item_rating"),
        CheckConstraint("progress_current >= 0", name="item_progress_nonneg"),
    )


class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[uuid.UUID] = _pk()
    destination: Mapped[str] = mapped_column(String(200))
    start: Mapped[Day | None] = mapped_column(Date)
    end: Mapped[Day | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="idea")
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (CheckConstraint("status in ('idea','planned','booked','done')", name="trip_status"),)


class TripItem(Base):
    __tablename__ = "trip_items"
    id: Mapped[uuid.UUID] = _pk()
    trip_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="todo")
    label: Mapped[str] = mapped_column(String(300))
    date: Mapped[Day | None] = mapped_column(Date)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    done: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (
        CheckConstraint("kind in ('flight','stay','activity','todo','other')", name="trip_item_kind"),
        CheckConstraint("cost is null or cost >= 0", name="trip_item_cost"),
    )


class Goal(Base):
    """A North Star goal: a target to reach by a deadline."""

    __tablename__ = "goals"
    id: Mapped[uuid.UUID] = _pk()
    title: Mapped[str] = mapped_column(String(300))
    area: Mapped[str] = mapped_column(String(100), default="")
    unit: Mapped[str] = mapped_column(String(30), default="")
    target: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    current: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    start: Mapped[Day] = mapped_column(Date)
    deadline: Mapped[Day] = mapped_column(Date)
    __table_args__ = (
        CheckConstraint("target > 0", name="goal_target_positive"),
        CheckConstraint("current >= 0", name="goal_current_nonneg"),
        CheckConstraint("deadline > start", name="goal_dates"),
    )


class Metric(Base):
    """Something you log every week (focus hours, sport sessions, sleep…)."""

    __tablename__ = "metrics"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(30), default="")
    target: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    min_viable: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (CheckConstraint("target > 0", name="metric_target_positive"),)


class WeekCheck(Base):
    __tablename__ = "week_checks"
    id: Mapped[uuid.UUID] = _pk()
    week_start: Mapped[Day] = mapped_column(Date, unique=True)
    energy: Mapped[int | None] = mapped_column()
    win: Mapped[str] = mapped_column(Text, default="")
    blocker: Mapped[str] = mapped_column(Text, default="")
    focus_next: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (CheckConstraint("energy is null or (energy between 1 and 5)", name="week_energy"),)


class WeekValue(Base):
    __tablename__ = "week_values"
    id: Mapped[uuid.UUID] = _pk()
    check_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("week_checks.id", ondelete="CASCADE"), index=True)
    metric_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("metrics.id", ondelete="CASCADE"), index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    __table_args__ = (
        UniqueConstraint("check_id", "metric_id", name="week_value_unique"),
        CheckConstraint("value >= 0", name="week_value_nonneg"),
    )


# --- personal money: net worth ----------------------------------------------------------------
class Account(Base):
    """Something you own or owe: a bank account, a brokerage account, a car, a loan…"""

    __tablename__ = "accounts"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(15))
    institution: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (
        CheckConstraint(
            "type in ('cash','savings','investment','retirement','crypto','property','vehicle','other_asset',"
            "'loan','mortgage','credit_card','other_debt')",
            name="account_type",
        ),
    )


class BalanceSnapshot(Base):
    """An account's balance on a given day. One per account per day."""

    __tablename__ = "balance_snapshots"
    id: Mapped[uuid.UUID] = _pk()
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    date: Mapped[Day] = mapped_column(Date)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    __table_args__ = (UniqueConstraint("account_id", "date", name="balance_one_per_day"),)


class Fund(Base):
    """A savings pot: money earmarked for a purpose (travel, emergency, Hajj…)."""

    __tablename__ = "funds"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(12), default="other")
    target: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    deadline: Mapped[Day | None] = mapped_column(Date)
    trip_id: Mapped[uuid.UUID | None] = _fk("trips")
    notes: Mapped[str] = mapped_column(Text, default="")
    # automation: a fixed amount every month and/or a share of each personal income, from auto_start on
    monthly_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    monthly_day: Mapped[int] = mapped_column(default=1, server_default="1")
    income_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    auto_start: Mapped[Day | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (
        CheckConstraint("monthly_amount is null or monthly_amount >= 0", name="fund_monthly_nonneg"),
        CheckConstraint("monthly_day between 1 and 28", name="fund_monthly_day"),
        CheckConstraint("income_pct is null or (income_pct between 0 and 100)", name="fund_income_pct"),
        CheckConstraint(
            "kind in ('travel','emergency','hajj','car','home','education','gifts','charity','purchase',"
            "'wedding','other')",
            name="fund_kind",
        ),
        CheckConstraint("target > 0", name="fund_target_positive"),
    )


class FundContribution(Base):
    """Money put into (positive) or taken out of (negative) a fund."""

    __tablename__ = "fund_contributions"
    id: Mapped[uuid.UUID] = _pk()
    fund_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("funds.id", ondelete="CASCADE"), index=True)
    date: Mapped[Day] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    __table_args__ = (CheckConstraint("amount <> 0", name="fund_contribution_nonzero"),)
