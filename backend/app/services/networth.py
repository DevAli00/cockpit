from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, BalanceSnapshot
from app.domain import networth as nw
from app.schemas_money import AccountOut, HistoryOut, NetWorthSummary, TypeTotal
from app.services import crud
from app.services.errors import InvalidError

STALE_AFTER_DAYS = 45  # nudge to update balances roughly monthly
CHANGE_WINDOW = timedelta(days=30)


def _kind(t: str) -> str:
    return "liability" if nw.is_liability(t) else "asset"  # type: ignore[arg-type]


async def _snapshots(s: AsyncSession) -> list[BalanceSnapshot]:
    return list((await s.scalars(select(BalanceSnapshot))).all())


async def list_accounts(s: AsyncSession) -> list[AccountOut]:
    accounts = await crud.list_all(s, Account, Account.created_at, Account.id)
    latest: dict[uuid.UUID, BalanceSnapshot] = {}
    for b in await _snapshots(s):
        if b.account_id not in latest or b.date > latest[b.account_id].date:
            latest[b.account_id] = b
    out = []
    for a in accounts:
        snap = latest.get(a.id)
        out.append(
            AccountOut.model_validate(a).model_copy(
                update={
                    "kind": _kind(a.type),
                    "balance": snap.balance if snap else None,
                    "as_of": snap.date if snap else None,
                }
            )
        )
    return out


async def account_out(s: AsyncSession, account: Account) -> AccountOut:
    return next(a for a in await list_accounts(s) if a.id == account.id)


async def set_balances(s: AsyncSession, at: date, balances: dict[uuid.UUID, object], today: date) -> None:
    """Upsert one balance per account for `at`; a second entry on the same day replaces the first."""
    if at > today:
        raise InvalidError("balances cannot be dated in the future")
    known = set((await s.scalars(select(Account.id).where(Account.id.in_(balances)))).all())
    if set(balances) - known:
        raise InvalidError("unknown account in balances")
    existing = {
        b.account_id: b
        for b in (await s.scalars(
            select(BalanceSnapshot).where(BalanceSnapshot.date == at, BalanceSnapshot.account_id.in_(balances))
        )).all()
    }
    for account_id, value in balances.items():
        if account_id in existing:
            existing[account_id].balance = value  # type: ignore[assignment]
        else:
            s.add(BalanceSnapshot(account_id=account_id, date=at, balance=value))
    await s.commit()


async def account_balances(s: AsyncSession, account_id: uuid.UUID) -> list[BalanceSnapshot]:
    stmt = select(BalanceSnapshot).where(BalanceSnapshot.account_id == account_id).order_by(BalanceSnapshot.date.desc())
    return list((await s.scalars(stmt)).all())


async def summary(s: AsyncSession, today: date) -> NetWorthSummary:
    rows = await crud.list_all(s, Account, Account.created_at)
    accounts = [nw.Account(id=a.id, type=a.type) for a in rows]  # type: ignore[arg-type]
    snaps = [nw.Snapshot(account_id=b.account_id, at=b.date, balance=b.balance) for b in await _snapshots(s)]

    now = nw.latest_balances(snaps, today)
    total = nw.net_worth(accounts, now)
    before = nw.latest_balances(snaps, today - CHANGE_WINDOW)
    change = total.net - nw.net_worth(accounts, before).net if before else None
    return NetWorthSummary(
        assets=total.assets, liabilities=total.liabilities, net=total.net, change_30d=change,
        by_type=[
            TypeTotal(type=t, kind=_kind(t), amount=amt)  # type: ignore[arg-type]
            for t, amt in nw.allocation(accounts, now)
        ],
        history=[
            HistoryOut(at=p.at, assets=p.assets, liabilities=p.liabilities, net=p.net)
            for p in nw.history(accounts, snaps, today)
        ],
        stale_accounts=len(nw.stale_accounts(accounts, snaps, today, STALE_AFTER_DAYS)),
    )
