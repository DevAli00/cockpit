from datetime import date, timedelta

from httpx import AsyncClient

from tests.test_api_core import mk

TODAY = date.today()
FIRST = TODAY.replace(day=1)


def iso(d: date) -> str:
    return d.isoformat()


async def fund(api: AsyncClient, **kw) -> dict:  # type: ignore[type-arg]
    return await mk(api, "/api/funds", **{"name": "F", "kind": "travel", "target": "10000", **kw})


async def get_fund(api: AsyncClient, fid: str) -> dict:  # type: ignore[type-arg]
    return next(f for f in (await api.get("/api/funds")).json() if f["id"] == fid)


async def test_expense_paid_from_fund_lowers_it_and_editing_the_expense_updates_it(api: AsyncClient) -> None:
    f = await fund(api)
    await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(TODAY), amount="500")
    e = await mk(api, "/api/entries", date=iso(TODAY), label="Flight", type="opex", category="Travel",
                 amount="300", scope="personal", fund_id=f["id"])
    assert (await get_fund(api, f["id"]))["balance"] == "200.00"
    await api.patch(f"/api/entries/{e['id']}", json={"amount": "350"})
    assert (await get_fund(api, f["id"]))["balance"] == "150.00"
    await api.delete(f"/api/entries/{e['id']}")
    assert (await get_fund(api, f["id"]))["balance"] == "500.00"


async def test_income_routed_into_a_fund(api: AsyncClient) -> None:
    f = await fund(api, kind="gifts", name="Eid")
    await mk(api, "/api/entries", date=iso(TODAY), label="Eid money", type="revenue", category="Gifts",
             amount="150", scope="personal", fund_id=f["id"])
    assert (await get_fund(api, f["id"]))["balance"] == "150.00"


async def test_business_transactions_cannot_touch_funds(api: AsyncClient) -> None:
    f = await fund(api)
    r = await api.post("/api/entries", json={"date": iso(TODAY), "label": "x", "type": "opex", "category": "c",
                                             "amount": "1", "fund_id": f["id"]})
    assert r.status_code == 422


async def test_monthly_rule_fills_the_fund_automatically(api: AsyncClient) -> None:
    start = FIRST - timedelta(days=40)  # somewhere in the month before last
    f = await fund(api, monthly_amount="200", monthly_day=1, auto_start=iso(start))
    got = await get_fund(api, f["id"])
    # deposits on the 1st of each month after `start`, up to today: last month's and this month's
    assert got["balance"] == "400.00"
    ledger = (await api.get(f"/api/funds/{f['id']}/ledger")).json()
    assert {m["source"] for m in ledger} == {"monthly"} and len(ledger) == 2


async def test_income_share_rule_and_cap_at_100_percent(api: AsyncClient) -> None:
    f = await fund(api, kind="emergency", income_pct="10", auto_start=iso(FIRST))
    await mk(api, "/api/entries", date=iso(FIRST), label="Salary", type="revenue", category="Salary",
             amount="3000", scope="personal")
    await mk(api, "/api/entries", date=iso(FIRST), label="Invoice", type="revenue", category="Services",
             amount="5000")  # business income is not shared
    assert (await get_fund(api, f["id"]))["balance"] == "300.00"
    assert (await api.post("/api/funds", json={"name": "G", "kind": "gifts", "target": "1", "income_pct": "95"})).status_code == 422
    assert (await api.patch(f"/api/funds/{f['id']}", json={"income_pct": "100"})).status_code == 200


async def test_changing_a_rule_does_not_rewrite_the_past(api: AsyncClient) -> None:
    start = FIRST - timedelta(days=40)
    f = await fund(api, monthly_amount="200", monthly_day=1, auto_start=iso(start))
    before = (await get_fund(api, f["id"]))["balance"]
    r = await api.patch(f"/api/funds/{f['id']}", json={"monthly_amount": "50"})
    assert r.status_code == 200, r.text
    after = r.json()
    # past deposits were frozen at 200 each; the new 50 only applies from today on
    assert after["auto_start"] == iso(TODAY)
    # deposits dated before today are frozen as they were; only a deposit due today follows the new rule
    expected = float(before) - (200 - 50 if TODAY.day == 1 else 0)
    assert float(after["balance"]) == expected
    sources = {m["source"] for m in (await api.get(f"/api/funds/{f['id']}/ledger")).json()}
    assert "manual" in sources


async def test_money_dashboard_shows_what_went_to_funds_and_what_is_left(api: AsyncClient) -> None:
    travel = await fund(api, monthly_amount="200", monthly_day=1, auto_start=iso(FIRST))
    await mk(api, "/api/entries", date=iso(FIRST), label="Salary", type="revenue", category="Salary", amount="3000", scope="personal")
    await mk(api, "/api/entries", date=iso(FIRST), label="Rent", type="opex", category="Housing", amount="800", scope="personal")
    await mk(api, "/api/entries", date=iso(FIRST), label="Flight", type="opex", category="Travel", amount="150",
             scope="personal", fund_id=travel["id"])
    s = (await api.get("/api/finance/summary?period=month&scope=personal")).json()
    assert s["totals"]["revenue"] == "3000.00" and s["totals"]["opex"] == "950.00"
    assert s["funds"]["to_funds"] == "200.00"  # monthly saving
    assert s["funds"]["from_funds"] == "150.00"  # flight paid from the fund
    # 3000 income - 950 spent - 200 set aside + 150 paid by the fund instead of your pocket
    assert s["funds"]["left_over"] == "2000.00"
    biz = (await api.get("/api/finance/summary?period=month")).json()
    assert biz["funds"] is None


async def test_deleting_a_fund_unlinks_its_transactions(api: AsyncClient) -> None:
    f = await fund(api)
    e = await mk(api, "/api/entries", date=iso(TODAY), label="Hotel", type="opex", category="Travel",
                 amount="90", scope="personal", fund_id=f["id"])
    await api.delete(f"/api/funds/{f['id']}")
    entries = (await api.get("/api/entries")).json()
    assert entries[0]["id"] == e["id"] and entries[0]["fund_id"] is None


async def test_backup_keeps_fund_links_and_rules(api: AsyncClient) -> None:
    f = await fund(api, monthly_amount="25", income_pct="5", auto_start=iso(FIRST))
    await mk(api, "/api/entries", date=iso(TODAY), label="Gift", type="opex", category="Gifts", amount="10",
             scope="personal", fund_id=f["id"])
    snap = (await api.get("/api/backup")).json()
    assert snap["funds"][0]["income_pct"] == "5.00" and snap["entries"][0]["fund_id"] == f["id"]
    assert (await api.post("/api/backup", json=snap)).status_code == 204
    assert (await api.get("/api/backup")).json() == snap
