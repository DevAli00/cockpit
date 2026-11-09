"""API contracts for personal money: accounts, balances and net worth."""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.networth import AccountType
from app.schemas import ORM, Patch, Text

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Short = Annotated[str, StringConstraints(max_length=200)]
# Balances may be negative (an overdrawn current account); bounded to the column's precision.
Balance = Annotated[Decimal, Field(max_digits=14, decimal_places=2)]
Kind = Literal["asset", "liability"]


class AccountIn(BaseModel):
    name: Name
    type: AccountType
    institution: Short = ""
    notes: Text = ""


class AccountPatch(Patch):
    name: Name | None = None
    type: AccountType | None = None
    institution: Short | None = None
    notes: Text | None = None


class AccountOut(AccountIn, ORM):
    id: uuid.UUID
    kind: Kind = "asset"
    balance: Decimal | None = None
    as_of: dt.date | None = None


class BalanceIn(BaseModel):
    date: dt.date
    balance: Balance


class BalanceOut(BalanceIn, ORM):
    id: uuid.UUID
    account_id: uuid.UUID


class BulkBalancesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: dt.date
    balances: dict[uuid.UUID, Balance]


class TypeTotal(BaseModel):
    type: AccountType
    kind: Kind
    amount: Decimal


class HistoryOut(BaseModel):
    at: dt.date
    assets: Decimal
    liabilities: Decimal
    net: Decimal


class NetWorthSummary(BaseModel):
    assets: Decimal
    liabilities: Decimal
    net: Decimal
    change_30d: Decimal | None
    by_type: list[TypeTotal]
    history: list[HistoryOut]
    stale_accounts: int


# --- savings funds ----------------------------------------------------------------------------
FundKind = Literal[
    "travel", "emergency", "hajj", "car", "home", "education", "gifts", "charity", "purchase", "wedding", "other",
]
FundAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Movement = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]


Pct = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]
Day28 = Annotated[int, Field(ge=1, le=28)]  # 28 so a rule fires in every month, February included
MonthlyAmount = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class FundIn(BaseModel):
    name: Name
    kind: FundKind = "other"
    target: FundAmount
    deadline: dt.date | None = None
    trip_id: uuid.UUID | None = None
    notes: Text = ""
    monthly_amount: MonthlyAmount | None = None
    monthly_day: Day28 = 1
    income_pct: Pct | None = None
    auto_start: dt.date | None = None


class FundPatch(Patch):
    name: Name | None = None
    kind: FundKind | None = None
    target: FundAmount | None = None
    deadline: dt.date | None = None
    trip_id: uuid.UUID | None = None
    notes: Text | None = None
    monthly_amount: MonthlyAmount | None = None
    monthly_day: Day28 | None = None
    income_pct: Pct | None = None


class FundOut(FundIn, ORM):
    id: uuid.UUID
    balance: Decimal = Decimal(0)
    remaining: Decimal = Decimal(0)
    progress: float = 0.0
    funded: bool = False
    monthly_needed: Decimal | None = None
    weekly_needed: Decimal | None = None
    contributions: int = 0


class ContributionIn(BaseModel):
    date: dt.date
    amount: Movement
    note: Annotated[str, StringConstraints(max_length=300)] = ""


class ContributionOut(ContributionIn, ORM):
    id: uuid.UUID
    fund_id: uuid.UUID


class MovementOut(BaseModel):
    date: dt.date
    amount: Decimal
    source: Literal["manual", "monthly", "income_share", "expense", "income"]
    label: str
    ref: str | None
