from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient


async def mk(api: AsyncClient, path: str, **body):  # type: ignore[no-untyped-def]
    r = await api.post(path, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def test_client_crud_and_validation(api: AsyncClient) -> None:
    c = await mk(api, "/api/clients", name="Acme", color="#2f6fde")
    assert (await api.get("/api/clients")).json()[0]["id"] == c["id"]
    r = await api.patch(f"/api/clients/{c['id']}", json={"name": "Acme Ltd"})
    assert r.json()["name"] == "Acme Ltd" and r.json()["color"] == "#2f6fde"
    assert (await api.post("/api/clients", json={"name": "", "color": "#fff000"})).status_code == 422
    assert (await api.post("/api/clients", json={"name": "x", "color": "red"})).status_code == 422
    assert (await api.delete(f"/api/clients/{c['id']}")).status_code == 204
    assert (await api.get(f"/api/clients/{c['id']}")).status_code == 404


async def test_deleting_client_keeps_its_projects_and_tasks(api: AsyncClient) -> None:
    c = await mk(api, "/api/clients", name="Acme", color="#2f6fde")
    p = await mk(api, "/api/projects", name="Site", client_id=c["id"])
    t = await mk(api, "/api/tasks", title="Wireframes", client_id=c["id"])
    await api.delete(f"/api/clients/{c['id']}")
    assert (await api.get(f"/api/projects/{p['id']}")).json()["client_id"] is None
    assert (await api.get(f"/api/tasks/{t['id']}")).json()["client_id"] is None


async def test_unknown_foreign_key_is_a_422_not_a_500(api: AsyncClient) -> None:
    r = await api.post(
        "/api/tasks", json={"title": "x", "client_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert r.status_code == 422


async def test_project_brief_and_journal(api: AsyncClient) -> None:
    p = await mk(api, "/api/projects", name="Site", brief={"goal": "Launch"})
    assert p["brief"]["goal"] == "Launch" and p["brief"]["context"] == ""
    n = await mk(api, f"/api/projects/{p['id']}/notes", kind="call", body="Kickoff", date="2026-03-01")
    notes = (await api.get(f"/api/projects/{p['id']}/notes")).json()
    assert [x["id"] for x in notes] == [n["id"]]
    assert (await api.post(f"/api/projects/{p['id']}/notes", json={"kind": "tweet", "body": "x", "date": "2026-03-01"})).status_code == 422
    await api.delete(f"/api/projects/{p['id']}")
    assert (await api.get(f"/api/projects/{p['id']}/notes")).status_code == 404


async def test_new_projects_appear_on_top(api: AsyncClient) -> None:
    a = await mk(api, "/api/projects", name="A")
    b = await mk(api, "/api/projects", name="B")
    assert [p["id"] for p in (await api.get("/api/projects")).json()] == [b["id"], a["id"]]


async def test_task_positions_increase_and_done_at_follows_column(api: AsyncClient) -> None:
    a = await mk(api, "/api/tasks", title="A")
    b = await mk(api, "/api/tasks", title="B")
    assert b["position"] > a["position"]
    moved = (await api.post(f"/api/tasks/{a['id']}/move", json={"col": "done"})).json()
    assert moved["col"] == "done" and moved["done_at"] is not None
    back = (await api.post(f"/api/tasks/{a['id']}/move", json={"col": "todo"})).json()
    assert back["done_at"] is None


async def test_move_before_another_card_reorders(api: AsyncClient) -> None:
    a, b, c = [await mk(api, "/api/tasks", title=t) for t in "ABC"]
    await api.post(f"/api/tasks/{c['id']}/move", json={"col": "todo", "before_id": b["id"]})
    order = [t["title"] for t in (await api.get("/api/tasks")).json() if t["col"] == "todo"]
    assert order == ["A", "C", "B"]
    await api.post(f"/api/tasks/{c['id']}/move", json={"col": "todo", "before_id": a["id"]})
    order = [t["title"] for t in (await api.get("/api/tasks")).json() if t["col"] == "todo"]
    assert order == ["C", "A", "B"]


async def test_repeated_moves_never_collapse_ordering(api: AsyncClient) -> None:
    a, b, c = [await mk(api, "/api/tasks", title=t) for t in "ABC"]
    # Keep squeezing a card between A and the previously moved one: forces rebalancing.
    anchor = b
    for _ in range(45):
        await api.post(f"/api/tasks/{c['id']}/move", json={"col": "todo", "before_id": anchor["id"]})
        await api.post(f"/api/tasks/{b['id']}/move", json={"col": "todo", "before_id": c["id"]})
    order = [t["title"] for t in (await api.get("/api/tasks")).json() if t["col"] == "todo"]
    assert sorted(order) == ["A", "B", "C"]
    positions = [t["position"] for t in (await api.get("/api/tasks")).json()]
    assert len(set(positions)) == 3


async def test_move_before_card_in_other_column_is_rejected(api: AsyncClient) -> None:
    a = await mk(api, "/api/tasks", title="A")
    b = await mk(api, "/api/tasks", title="B", col="blocked")
    r = await api.post(f"/api/tasks/{a['id']}/move", json={"col": "todo", "before_id": b["id"]})
    assert r.status_code == 422


async def test_old_done_tasks_leave_the_board_but_are_kept(api: AsyncClient, anon: AsyncClient) -> None:
    from app.db.models import Task

    t = await mk(api, "/api/tasks", title="Old")
    await api.post(f"/api/tasks/{t['id']}/move", json={"col": "done"})
    factory = anon._transport.app.state.session_factory  # type: ignore[attr-defined]
    async with factory() as s:
        row = await s.get(Task, __import__("uuid").UUID(t["id"]))
        row.done_at = datetime.now(UTC) - timedelta(days=10)
        await s.commit()
    assert (await api.get("/api/tasks")).json() == []
    assert len((await api.get("/api/tasks?include_archived=true")).json()) == 1


async def test_finance_summary_combines_entries_and_recurring(api: AsyncClient) -> None:
    today = date.today()
    await mk(api, "/api/entries", date=today.isoformat(), label="Invoice", type="revenue", category="Services", amount="1000.00")
    await mk(api, "/api/entries", date=today.isoformat(), label="Freelancer", type="direct", category="Subcontracting", amount="200.00")
    await mk(api, "/api/recurring", label="Hosting", type="opex", category="Software & SaaS", amount="50.00", frequency="monthly", start=today.replace(day=1).isoformat())
    s = (await api.get("/api/finance/summary?period=month")).json()
    assert s["totals"]["revenue"] == "1000.00"
    assert s["totals"]["direct"] == "200.00"
    assert s["totals"]["opex"] == "50.00"
    assert s["totals"]["net"] == "750.00"
    assert len(s["transactions"]) == 3
    assert {c["category"] for c in s["by_category"]} == {"Services", "Subcontracting", "Software & SaaS"}


async def test_finance_ignores_future_entries_and_respects_period(api: AsyncClient) -> None:
    today = date.today()
    await mk(api, "/api/entries", date=(today + timedelta(days=40)).isoformat(), label="Planned", type="revenue", category="Services", amount="999")
    await mk(api, "/api/entries", date=(today - timedelta(days=200)).isoformat(), label="Old", type="revenue", category="Services", amount="10")
    month = (await api.get("/api/finance/summary?period=month")).json()
    allt = (await api.get("/api/finance/summary?period=all")).json()
    assert month["totals"]["revenue"] == "0"
    assert allt["totals"]["revenue"] == "10.00"
    assert (await api.get("/api/finance/summary?period=week")).status_code == 422


async def test_entry_validation(api: AsyncClient) -> None:
    base = dict(date="2026-03-01", label="x", type="revenue", category="Services", amount="10")
    assert (await api.post("/api/entries", json={**base, "amount": "-5"})).status_code == 422
    assert (await api.post("/api/entries", json={**base, "type": "gift"})).status_code == 422
    assert (await api.post("/api/entries", json={**base, "amount": "1e99"})).status_code == 422


async def test_search_spans_everything_and_escapes_wildcards(api: AsyncClient) -> None:
    c = await mk(api, "/api/clients", name="Zephyr Corp", color="#112233")
    p = await mk(api, "/api/projects", name="Zephyr rebrand", client_id=c["id"])
    await mk(api, f"/api/projects/{p['id']}/notes", kind="note", body="zephyr wants blue", date="2026-03-01")
    await mk(api, "/api/tasks", title="Send zephyr invoice")
    await mk(api, "/api/entries", date="2026-03-01", label="Zephyr deposit", type="revenue", category="Services", amount="5")
    kinds = {r["kind"] for r in (await api.get("/api/search?q=zephyr")).json()}
    assert kinds == {"client", "project", "note", "task", "entry"}
    assert (await api.get("/api/search?q=%25%25")).json() == []  # literal '%%' matches nothing
    assert (await api.get("/api/search?q=z")).status_code == 422


async def test_profile_defaults_and_update(api: AsyncClient) -> None:
    assert (await api.get("/api/profile")).json()["currency"] == "EUR"
    r = await api.put("/api/profile", json={"name": "Ali", "company": "Co", "currency": "USD"})
    assert r.json()["currency"] == "USD"
    assert (await api.put("/api/profile", json={"currency": "XXXX"})).status_code == 422


async def test_backup_roundtrip_replaces_data(api: AsyncClient) -> None:
    c = await mk(api, "/api/clients", name="Acme", color="#2f6fde")
    p = await mk(api, "/api/projects", name="Site", client_id=c["id"])
    await mk(api, f"/api/projects/{p['id']}/notes", kind="note", body="hello", date="2026-03-01")
    await mk(api, "/api/tasks", title="T", project_id=p["id"])
    await mk(api, "/api/entries", date="2026-03-01", label="E", type="revenue", category="Services", amount="5", project_id=p["id"])
    snapshot = (await api.get("/api/backup")).json()
    assert snapshot["version"] == 1
    await mk(api, "/api/clients", name="Extra", color="#000000")
    r = await api.post("/api/backup", json=snapshot); assert r.status_code == 204, r.text
    assert [x["name"] for x in (await api.get("/api/clients")).json()] == ["Acme"]
    assert (await api.get("/api/backup")).json()["tasks"] == snapshot["tasks"]


async def test_backup_with_dangling_reference_is_rejected_and_changes_nothing(api: AsyncClient) -> None:
    await mk(api, "/api/clients", name="Keep", color="#2f6fde")
    snap = (await api.get("/api/backup")).json()
    snap["tasks"] = [{**{"id": "11111111-1111-1111-1111-111111111111", "title": "x", "col": "todo", "client_id": None, "project_id": "22222222-2222-2222-2222-222222222222", "due": None, "note": "", "position": 1.0, "done_at": None}}]
    assert (await api.post("/api/backup", json=snap)).status_code == 422
    assert [x["name"] for x in (await api.get("/api/clients")).json()] == ["Keep"]


async def test_backup_wrong_version_rejected(api: AsyncClient) -> None:
    snap = (await api.get("/api/backup")).json()
    assert (await api.post("/api/backup", json={**snap, "version": 99})).status_code == 422
