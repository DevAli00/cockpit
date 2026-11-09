"""Authenticated routes for personal money: accounts, balances and net worth."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import Session, current_user
from app.db.models import Account, BalanceSnapshot, Fund, FundContribution
from app.schemas_money import (
    AccountIn, AccountOut, AccountPatch, BalanceIn, BalanceOut, BulkBalancesIn, ContributionIn,
    ContributionOut, FundIn, FundOut, FundPatch, MovementOut, NetWorthSummary,
)
from app.services import crud, funds, networth

router = APIRouter(dependencies=[Depends(current_user)])
NO_CONTENT = status.HTTP_204_NO_CONTENT


@router.get("/networth/accounts", response_model=list[AccountOut])
async def list_accounts(s: Session) -> list[AccountOut]:
    return await networth.list_accounts(s)


@router.post("/networth/accounts", response_model=AccountOut, status_code=201)
async def create_account(body: AccountIn, s: Session) -> AccountOut:
    return await networth.account_out(s, await crud.create(s, Account, body.model_dump()))


@router.patch("/networth/accounts/{id}", response_model=AccountOut)
async def patch_account(id: uuid.UUID, body: AccountPatch, s: Session) -> AccountOut:
    account = await crud.update(s, await crud.get_or_404(s, Account, id), body.model_dump(exclude_unset=True))
    return await networth.account_out(s, account)


@router.delete("/networth/accounts/{id}", status_code=NO_CONTENT)
async def delete_account(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Account, id))


@router.get("/networth/accounts/{id}/balances", response_model=list[BalanceOut])
async def list_balances(id: uuid.UUID, s: Session) -> list[BalanceSnapshot]:
    await crud.get_or_404(s, Account, id)
    return await networth.account_balances(s, id)


@router.post("/networth/accounts/{id}/balances", response_model=BalanceOut, status_code=201)
async def add_balance(id: uuid.UUID, body: BalanceIn, s: Session) -> BalanceSnapshot:
    await crud.get_or_404(s, Account, id)
    await networth.set_balances(s, body.date, {id: body.balance}, dt.date.today())
    return next(b for b in await networth.account_balances(s, id) if b.date == body.date)


@router.delete("/networth/balances/{id}", status_code=NO_CONTENT)
async def delete_balance(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, BalanceSnapshot, id))


@router.post("/networth/update", status_code=NO_CONTENT)
async def bulk_update(body: BulkBalancesIn, s: Session) -> None:
    """The monthly ritual: type every account's balance for one date in a single save."""
    await networth.set_balances(s, body.date, dict(body.balances), dt.date.today())


@router.get("/networth/summary", response_model=NetWorthSummary)
async def summary(s: Session) -> NetWorthSummary:
    return await networth.summary(s, dt.date.today())


# --- savings funds ----------------------------------------------------------------------------
@router.get("/funds", response_model=list[FundOut])
async def list_funds(s: Session, trip_id: uuid.UUID | None = None) -> list[FundOut]:
    return await funds.list_funds(s, dt.date.today(), trip_id)


@router.post("/funds", response_model=FundOut, status_code=201)
async def create_fund(body: FundIn, s: Session) -> FundOut:
    today = dt.date.today()
    return await funds.fund_out(s, await funds.create_fund(s, body.model_dump(), today), today)


@router.patch("/funds/{id}", response_model=FundOut)
async def patch_fund(id: uuid.UUID, body: FundPatch, s: Session) -> FundOut:
    today = dt.date.today()
    fund = await funds.update_fund(s, await crud.get_or_404(s, Fund, id), body.model_dump(exclude_unset=True), today)
    return await funds.fund_out(s, fund, today)


@router.delete("/funds/{id}", status_code=NO_CONTENT)
async def delete_fund(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Fund, id))


@router.get("/funds/{id}/contributions", response_model=list[ContributionOut])
async def list_contributions(id: uuid.UUID, s: Session) -> list[FundContribution]:
    await crud.get_or_404(s, Fund, id)
    return await funds.contributions(s, id)


@router.post("/funds/{id}/contributions", response_model=ContributionOut, status_code=201)
async def add_contribution(id: uuid.UUID, body: ContributionIn, s: Session) -> FundContribution:
    return await funds.add_contribution(s, await crud.get_or_404(s, Fund, id), body, dt.date.today())


@router.delete("/funds/contributions/{id}", status_code=NO_CONTENT)
async def delete_contribution(id: uuid.UUID, s: Session) -> None:
    await funds.delete_contribution(s, await crud.get_or_404(s, FundContribution, id), dt.date.today())


@router.get("/funds/{id}/ledger", response_model=list[MovementOut])
async def fund_ledger(id: uuid.UUID, s: Session) -> list[MovementOut]:
    """Every movement: manual, automatic (monthly / share of income) and linked transactions."""
    return await funds.ledger(s, await crud.get_or_404(s, Fund, id), dt.date.today())
