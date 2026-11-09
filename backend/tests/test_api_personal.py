from datetime import date, timedelta

from httpx import AsyncClient

from tests.test_api_core import mk

TODAY = date.today()


def iso(delta: int) -> str:
    return (TODAY + timedelta(days=delta)).isoformat()


# --- net worth ---------------------------------------------------------------------------------
async def test_accounts_report_kind_and_latest_balance(api: AsyncClient) -> None:
    a = await mk(api, "/api/networth/accounts", name="Livret A", type="savings", institution="Banque")
    assert a["kind"] == "asset" and a["balance"] is None and a["as_of"] is None
    loan = await mk(api, "/api/networth/accounts", name="Student loan", type="loan")
    assert loan["kind"] == "liability"
    await mk(api, f"/api/networth/accounts/{a['id']}/balances", date=iso(-40), balance="1000")
    await mk(api, f"/api/networth/accounts/{a['id']}/balances", date=iso(-5), balance="1500.5")
    got = {x["name"]: x for x in (await api.get("/api/networth/accounts")).json()}
    assert got["Livret A"]["balance"] == "1500.50" and got["Livret A"]["as_of"] == iso(-5)
    assert (await api.post("/api/networth/accounts", json={"name": "x", "type": "gold bar"})).status_code == 422


async def test_same_day_balance_replaces_instead_of_duplicating(api: AsyncClient) -> None:
    a = await mk(api, "/api/networth/accounts", name="PEA", type="investment")
    await mk(api, f"/api/networth/accounts/{a['id']}/balances", date=iso(0), balance="100")
    await mk(api, f"/api/networth/accounts/{a['id']}/balances", date=iso(0), balance="120")
    hist = (await api.get(f"/api/networth/accounts/{a['id']}/balances")).json()
    assert [h["balance"] for h in hist] == ["120.00"]


async def test_bulk_update_and_summary(api: AsyncClient) -> None:
    cash = await mk(api, "/api/networth/accounts", name="Current", type="cash")
    save = await mk(api, "/api/networth/accounts", name="Savings", type="savings")
    cc = await mk(api, "/api/networth/accounts", name="Card", type="credit_card")
    r = await api.post("/api/networth/update", json={"date": iso(-35), "balances": {cash["id"]: "1000", save["id"]: "5000"}})
    assert r.status_code == 204, r.text
    r = await api.post("/api/networth/update", json={"date": iso(0), "balances": {cash["id"]: "1200", save["id"]: "6000", cc["id"]: "300"}})
    assert r.status_code == 204
    s = (await api.get("/api/networth/summary")).json()
    assert (s["assets"], s["liabilities"], s["net"]) == ("7200.00", "300.00", "6900.00")
    assert s["change_30d"] == "900.00"  # 6900 now vs 6000 thirty days ago
    assert s["by_type"][0] == {"type": "savings", "amount": "6000.00", "kind": "asset"}
    assert s["history"][-1]["net"] == "6900.00" and len(s["history"]) >= 2
    assert s["stale_accounts"] == 0


async def test_bulk_update_validation(api: AsyncClient) -> None:
    ghost = "00000000-0000-0000-0000-000000000000"
    assert (await api.post("/api/networth/update", json={"date": iso(0), "balances": {ghost: "1"}})).status_code == 422
    assert (await api.post("/api/networth/update", json={"date": iso(3), "balances": {}})).status_code == 422  # no future balances


async def test_summary_flags_stale_accounts_and_handles_empty(api: AsyncClient) -> None:
    empty = (await api.get("/api/networth/summary")).json()
    assert empty["net"] == "0" and empty["history"] == [] and empty["change_30d"] is None
    a = await mk(api, "/api/networth/accounts", name="Old", type="savings")
    await mk(api, f"/api/networth/accounts/{a['id']}/balances", date=iso(-90), balance="10")
    await mk(api, "/api/networth/accounts", name="Never", type="cash")
    assert (await api.get("/api/networth/summary")).json()["stale_accounts"] == 2


async def test_deleting_account_removes_its_balances(api: AsyncClient) -> None:
    a = await mk(api, "/api/networth/accounts", name="Gone", type="crypto")
    b = await mk(api, f"/api/networth/accounts/{a['id']}/balances", date=iso(0), balance="99")
    await api.delete(f"/api/networth/accounts/{a['id']}")
    assert (await api.get("/api/networth/summary")).json()["net"] == "0"
    assert (await api.delete(f"/api/networth/balances/{b['id']}")).status_code == 404


# --- personal vs business money ----------------------------------------------------------------
async def test_entries_default_to_business_and_summary_filters_by_scope(api: AsyncClient) -> None:
    await mk(api, "/api/entries", date=iso(0), label="Invoice", type="revenue", category="Services", amount="1000")
    await mk(api, "/api/entries", date=iso(0), label="Salary", type="revenue", category="Salary", amount="2500", scope="personal")
    await mk(api, "/api/entries", date=iso(0), label="Groceries", type="opex", category="Groceries", amount="300", scope="personal")
    await mk(api, "/api/recurring", label="Rent", type="opex", category="Housing", amount="700", frequency="monthly", start=iso(0), scope="personal")
    biz = (await api.get("/api/finance/summary?period=month")).json()
    assert biz["totals"]["revenue"] == "1000.00" and biz["totals"]["opex"] == "0"
    me = (await api.get("/api/finance/summary?period=month&scope=personal")).json()
    assert me["totals"]["revenue"] == "2500.00" and me["totals"]["opex"] == "1000.00"
    assert me["totals"]["net_rate"] == "60.0"  # savings rate
    both = (await api.get("/api/finance/summary?period=month&scope=all")).json()
    assert both["totals"]["revenue"] == "3500.00"
    assert [e["label"] for e in (await api.get("/api/entries?scope=personal")).json()] == ["Groceries", "Salary"] or \
        {e["label"] for e in (await api.get("/api/entries?scope=personal")).json()} == {"Groceries", "Salary"}
    assert len((await api.get("/api/recurring?scope=business")).json()) == 0
    assert (await api.post("/api/entries", json={"date": iso(0), "label": "x", "type": "opex", "category": "c", "amount": "1", "scope": "family"})).status_code == 422


# --- profile, search, backup -------------------------------------------------------------------
async def test_profile_can_hide_business(api: AsyncClient) -> None:
    assert (await api.get("/api/profile")).json()["show_business"] is True
    r = await api.put("/api/profile", json={"name": "Ali", "currency": "EUR", "show_business": False})
    assert r.json()["show_business"] is False


async def test_networth_requires_login(anon: AsyncClient) -> None:
    for p in ("/api/networth/accounts", "/api/networth/summary"):
        assert (await anon.get(p)).status_code == 401


async def test_search_finds_accounts(api: AsyncClient) -> None:
    await mk(api, "/api/networth/accounts", name="Boursorama PEA", type="investment")
    assert {h["kind"] for h in (await api.get("/api/search?q=boursorama")).json()} == {"account"}


async def test_backup_roundtrip_includes_networth_and_scope(api: AsyncClient) -> None:
    a = await mk(api, "/api/networth/accounts", name="Savings", type="savings")
    await mk(api, f"/api/networth/accounts/{a['id']}/balances", date=iso(0), balance="42")
    await mk(api, "/api/entries", date=iso(0), label="Salary", type="revenue", category="Salary", amount="1", scope="personal")
    await api.put("/api/profile", json={"show_business": False})
    snap = (await api.get("/api/backup")).json()
    assert len(snap["accounts"]) == 1 and len(snap["balances"]) == 1 and snap["entries"][0]["scope"] == "personal"
    await api.delete(f"/api/networth/accounts/{a['id']}")
    assert (await api.post("/api/backup", json=snap)).status_code == 204
    assert (await api.get("/api/backup")).json() == snap
    assert (await api.get("/api/networth/summary")).json()["net"] == "42.00"


async def test_transaction_scope_can_be_switched(api: AsyncClient) -> None:
    e = await mk(api, "/api/entries", date=iso(0), label="Laptop", type="opex", category="Shopping", amount="900")
    assert (await api.patch(f"/api/entries/{e['id']}", json={"scope": "personal"})).json()["scope"] == "personal"
    assert (await api.get("/api/finance/summary?period=month")).json()["totals"]["opex"] == "0"
    r = await mk(api, "/api/recurring", label="Phone", type="opex", category="c", amount="20", frequency="monthly", start=iso(0))
    assert (await api.patch(f"/api/recurring/{r['id']}", json={"scope": "personal"})).json()["scope"] == "personal"
    assert (await api.patch(f"/api/entries/{e['id']}", json={"scope": "both"})).status_code == 422
