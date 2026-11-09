"""API contracts. Validation lives here, at the system boundary."""
from __future__ import annotations

import uuid
import datetime as dt
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.finance import EntryType, Frequency, Period, Totals
from app.domain.tasks import TaskColumn

Day = dt.date
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Text = Annotated[str, StringConstraints(max_length=20_000)]
Color = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
Money = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
ProjectStatus = Literal["Not started", "In progress", "On hold", "Done"]
Scope = Literal["business", "personal"]
NoteKind = Literal["note", "call", "decision", "feedback", "email"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Patch(BaseModel):
    """Base for PATCH bodies: only fields the client sent are applied."""

    model_config = ConfigDict(extra="forbid")


# --- auth / profile -------------------------------------------------------------------------
class LoginIn(BaseModel):
    email: Annotated[str, StringConstraints(max_length=320)]
    password: Annotated[str, StringConstraints(max_length=1024)]


class MeOut(BaseModel):
    email: str
    desktop: bool = False  # standalone app: no password, no sign-out


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, StringConstraints(max_length=200)] = ""
    email: Annotated[str, StringConstraints(max_length=320)] = ""
    company: Annotated[str, StringConstraints(max_length=200)] = ""
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")] = "EUR"
    show_business: bool = True


class ProfileOut(ProfileIn, ORM):
    pass


# --- clients ----------------------------------------------------------------------------------
class ClientIn(BaseModel):
    name: Name
    color: Color


class ClientPatch(Patch):
    name: Name | None = None
    color: Color | None = None


class ClientOut(ClientIn, ORM):
    id: uuid.UUID


# --- projects ---------------------------------------------------------------------------------
class Brief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    context: Text = ""
    goal: Text = ""
    deliverables: Text = ""
    out: Text = ""


class ProjectIn(BaseModel):
    name: Name
    client_id: uuid.UUID | None = None
    start: Day | None = None
    deadline: Day | None = None
    status: ProjectStatus = "Not started"
    brief: Brief = Field(default_factory=Brief)


class ProjectPatch(Patch):
    name: Name | None = None
    client_id: uuid.UUID | None = None
    start: Day | None = None
    deadline: Day | None = None
    status: ProjectStatus | None = None
    brief: Brief | None = None


class ProjectOut(ProjectIn, ORM):
    id: uuid.UUID
    position: float


class NoteIn(BaseModel):
    date: Day
    kind: NoteKind = "note"
    body: Text = ""


class NotePatch(Patch):
    date: Day | None = None
    kind: NoteKind | None = None
    body: Text | None = None


class NoteOut(NoteIn, ORM):
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: dt.datetime


# --- tasks ------------------------------------------------------------------------------------
class TaskIn(BaseModel):
    title: Title
    col: TaskColumn = "todo"
    client_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    due: Day | None = None
    note: Text = ""


class TaskPatch(Patch):
    title: Title | None = None
    client_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    due: Day | None = None
    note: Text | None = None


class TaskMoveIn(BaseModel):
    col: TaskColumn
    before_id: uuid.UUID | None = None


class TaskOut(TaskIn, ORM):
    id: uuid.UUID
    position: float
    done_at: dt.datetime | None
    created_at: dt.datetime


# --- finance ----------------------------------------------------------------------------------
class EntryIn(BaseModel):
    scope: Scope = "business"
    fund_id: uuid.UUID | None = None
    date: Day
    label: Title
    type: EntryType
    category: Name
    amount: Money
    project_id: uuid.UUID | None = None


class EntryPatch(Patch):
    scope: Scope | None = None
    fund_id: uuid.UUID | None = None
    date: Day | None = None
    label: Title | None = None
    type: EntryType | None = None
    category: Name | None = None
    amount: Money | None = None
    project_id: uuid.UUID | None = None


class EntryOut(EntryIn, ORM):
    id: uuid.UUID


class RecurringIn(BaseModel):
    scope: Scope = "business"
    fund_id: uuid.UUID | None = None
    label: Title
    type: EntryType
    category: Name
    amount: Money
    frequency: Frequency
    start: Day
    end: Day | None = None
    project_id: uuid.UUID | None = None


class RecurringPatch(Patch):
    scope: Scope | None = None
    fund_id: uuid.UUID | None = None
    label: Title | None = None
    type: EntryType | None = None
    category: Name | None = None
    amount: Money | None = None
    frequency: Frequency | None = None
    start: Day | None = None
    end: Day | None = None
    project_id: uuid.UUID | None = None


class RecurringOut(RecurringIn, ORM):
    id: uuid.UUID


class TxnOut(BaseModel):
    id: str
    date: Day
    label: str
    type: EntryType
    category: str
    amount: Decimal
    project_id: uuid.UUID | None
    recurring_id: uuid.UUID | None
    fund_id: uuid.UUID | None = None


class CategoryTotal(BaseModel):
    type: EntryType
    category: str
    amount: Decimal


class MonthTotal(BaseModel):
    month: str
    revenue: Decimal
    costs: Decimal


class TotalsOut(BaseModel):
    revenue: Decimal
    direct: Decimal
    opex: Decimal
    gross: Decimal
    net: Decimal
    gross_rate: Decimal
    net_rate: Decimal

    @classmethod
    def of(cls, t: Totals) -> TotalsOut:
        return cls(**{f: getattr(t, f) for f in cls.model_fields})


class FundFlow(BaseModel):
    to_funds: Decimal
    from_funds: Decimal
    left_over: Decimal


class FinanceSummary(BaseModel):
    period: Period
    start: Day | None
    totals: TotalsOut
    by_category: list[CategoryTotal]
    by_month: list[MonthTotal]
    transactions: list[TxnOut]
    funds: FundFlow | None = None  # personal money only


# --- search / backup --------------------------------------------------------------------------
class SearchHit(BaseModel):
    kind: Literal[
        "client", "project", "note", "task", "entry", "recurring", "path", "milestone", "item", "trip", "goal",
        "account", "fund",
    ]
    id: uuid.UUID
    title: str
    subtitle: str = ""
    project_id: uuid.UUID | None = None
