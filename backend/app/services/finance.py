from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.finance import Period, period_start, totals
from app.schemas import CategoryTotal, FinanceSummary, FundFlow, MonthTotal, TotalsOut, TxnOut
from app.services import funds
from app.services.ledger import load_txns


async def summarize(s: AsyncSession, period: Period, today: date, scope: str = "business") -> FinanceSummary:
    """`scope` is 'business', 'personal' or 'all'. Personal summaries also show money moved through funds."""
    start = period_start(period, today)
    txns = await load_txns(s, today, scope, start)
    txns.sort(key=lambda t: (t.date, t.id), reverse=True)

    by_cat: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    by_month: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"revenue": Decimal(0), "costs": Decimal(0)})
    for t in txns:
        by_cat[(t.type, t.category)] += t.amount
        by_month[t.date.strftime("%Y-%m")]["revenue" if t.type == "revenue" else "costs"] += t.amount

    t = totals(txns)
    flow = None
    if scope != "business":
        to_funds, from_funds = await funds.period_flow(s, start, today)
        # What is left to spend: income, minus spending, minus what you set aside,
        # plus spending that a fund paid for instead of your pocket.
        flow = FundFlow(
            to_funds=to_funds, from_funds=from_funds,
            left_over=t.revenue - t.direct - t.opex - to_funds + from_funds,
        )
    return FinanceSummary(
        period=period, start=start, totals=TotalsOut.of(t),
        by_category=[
            CategoryTotal(type=k[0], category=k[1], amount=v)  # type: ignore[arg-type]
            for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1])
        ],
        by_month=[MonthTotal(month=m, **v) for m, v in sorted(by_month.items())],
        transactions=[TxnOut(**asdict(t)) for t in txns],
        funds=flow,
    )
