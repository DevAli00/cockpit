from datetime import date, timedelta

from httpx import AsyncClient

from tests.test_api_core import mk

TODAY = date.today()


def iso(delta: int) -> str:
    return (TODAY + timedelta(days=delta)).isoformat()


async def test_fund_lifecycle_with_deposits_and_withdrawals(api: AsyncClient) -> None:
    f = await mk(api, "/api/funds", name="Travel fund", kind="travel", target="2400", deadline=iso(120))
    assert f["balance"] == "0" and f["progress"] == 0 and f["funded"] is False
    assert f["monthly_needed"] is not None and f["weekly_needed"] is not None
    await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(0), amount="600", note="October")
    await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(0), amount="-100", note="Flight deposit")
    got = (await api.get("/api/funds")).json()[0]
    assert got["balance"] == "500.00" and got["remaining"] == "1900.00" and got["contributions"] == 2
    hist = (await api.get(f"/api/funds/{f['id']}/contributions")).json()
    assert {h["note"] for h in hist} == {"October", "Flight deposit"}


async def test_withdrawal_cannot_go_below_zero_and_zero_amount_rejected(api: AsyncClient) -> None:
    f = await mk(api, "/api/funds", name="Emergency", kind="emergency", target="5000")
    await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(0), amount="100")
    r = await api.post(f"/api/funds/{f['id']}/contributions", json={"date": iso(0), "amount": "-150"})
    assert r.status_code == 422 and "below zero" in r.json()["detail"]
    assert (await api.post(f"/api/funds/{f['id']}/contributions", json={"date": iso(0), "amount": "0"})).status_code == 422
    assert (await api.post(f"/api/funds/{f['id']}/contributions", json={"date": iso(5), "amount": "1"})).status_code == 422


async def test_funded_flag_and_no_deadline(api: AsyncClient) -> None:
    f = await mk(api, "/api/funds", name="Eid gifts", kind="gifts", target="200")
    assert f["monthly_needed"] is None
    await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(0), amount="250")
    got = (await api.get("/api/funds")).json()[0]
    assert got["funded"] is True and got["progress"] == 1 and got["remaining"] == "0"


async def test_fund_validation(api: AsyncClient) -> None:
    assert (await api.post("/api/funds", json={"name": "x", "kind": "yacht", "target": "1"})).status_code == 422
    assert (await api.post("/api/funds", json={"name": "x", "kind": "other", "target": "0"})).status_code == 422
    ghost = "00000000-0000-0000-0000-000000000000"
    assert (await api.post("/api/funds", json={"name": "x", "kind": "travel", "target": "1", "trip_id": ghost})).status_code == 422


async def test_fund_linked_to_trip_survives_trip_deletion(api: AsyncClient) -> None:
    t = await mk(api, "/api/trips", destination="Morocco")
    f = await mk(api, "/api/funds", name="Morocco", kind="travel", target="1200", trip_id=t["id"])
    assert f["trip_id"] == t["id"]
    assert [x["id"] for x in (await api.get(f"/api/funds?trip_id={t['id']}")).json()] == [f["id"]]
    await api.delete(f"/api/trips/{t['id']}")
    assert (await api.get("/api/funds")).json()[0]["trip_id"] is None


async def test_deleting_contribution_and_fund(api: AsyncClient) -> None:
    f = await mk(api, "/api/funds", name="Car", kind="car", target="3000")
    c = await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(0), amount="300")
    assert (await api.delete(f"/api/funds/contributions/{c['id']}")).status_code == 204
    assert (await api.get("/api/funds")).json()[0]["balance"] == "0"
    await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(0), amount="5")
    await api.delete(f"/api/funds/{f['id']}")
    assert (await api.get("/api/funds")).json() == []


async def test_deleting_a_deposit_that_was_spent_is_refused(api: AsyncClient) -> None:
    f = await mk(api, "/api/funds", name="Umrah", kind="hajj", target="3000")
    dep = await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(0), amount="300")
    await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(0), amount="-200")
    assert (await api.delete(f"/api/funds/contributions/{dep['id']}")).status_code == 422


async def test_funds_require_login_search_and_backup(api: AsyncClient, anon: AsyncClient) -> None:
    f = await mk(api, "/api/funds", name="Hajj savings", kind="hajj", target="6000", notes="Inshallah 2028")
    await mk(api, f"/api/funds/{f['id']}/contributions", date=iso(0), amount="250")
    assert "fund" in {h["kind"] for h in (await api.get("/api/search?q=hajj")).json()}
    snap = (await api.get("/api/backup")).json()
    assert len(snap["funds"]) == 1 and len(snap["fund_contributions"]) == 1
    await api.delete(f"/api/funds/{f['id']}")
    assert (await api.post("/api/backup", json=snap)).status_code == 204
    assert (await api.get("/api/backup")).json() == snap
    api.cookies.clear()
    assert (await api.get("/api/funds")).status_code == 401
