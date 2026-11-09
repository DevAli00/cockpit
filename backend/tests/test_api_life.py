from datetime import date, timedelta

from httpx import AsyncClient

from tests.test_api_core import mk

TODAY = date.today()


def iso(delta: int) -> str:
    return (TODAY + timedelta(days=delta)).isoformat()


# --- learning ----------------------------------------------------------------------------------
async def test_paths_have_main_and_secondary_kinds_and_progress(api: AsyncClient) -> None:
    main = await mk(api, "/api/learning/paths", name="CPTS", kind="main")
    await mk(api, "/api/learning/paths", name="AI safety", kind="secondary")
    assert (await api.post("/api/learning/paths", json={"name": "x", "kind": "tertiary"})).status_code == 422

    for title, horizon, status in [("Pivoting module", "weekly", "done"), ("Path 100%", "monthly", "todo")]:
        await mk(api, f"/api/learning/paths/{main['id']}/milestones", title=title, horizon=horizon, status=status, due=iso(5))
    paths = {p["name"]: p for p in (await api.get("/api/learning/paths")).json()}
    assert paths["CPTS"]["milestones_total"] == 2 and paths["CPTS"]["milestones_done"] == 1
    assert paths["CPTS"]["progress"] == 0.5
    assert paths["AI safety"]["progress"] == 0


async def test_milestone_horizons_filter_and_overdue_flag(api: AsyncClient) -> None:
    p = await mk(api, "/api/learning/paths", name="OSCP", kind="main")
    for h in ("weekly", "monthly", "quarterly", "semester"):
        await mk(api, f"/api/learning/paths/{p['id']}/milestones", title=h, horizon=h, due=iso(-1))
    assert (await api.post(f"/api/learning/paths/{p['id']}/milestones", json={"title": "x", "horizon": "daily"})).status_code == 422
    q = (await api.get("/api/learning/milestones?horizon=quarterly")).json()
    assert [m["title"] for m in q] == ["quarterly"] and q[0]["overdue"] is True and q[0]["path_id"] == p["id"]
    done = (await api.patch(f"/api/learning/milestones/{q[0]['id']}", json={"status": "done"})).json()
    assert done["overdue"] is False


async def test_deleting_a_path_removes_milestones_but_keeps_items(api: AsyncClient) -> None:
    p = await mk(api, "/api/learning/paths", name="P", kind="secondary")
    await mk(api, f"/api/learning/paths/{p['id']}/milestones", title="m", horizon="weekly")
    it = await mk(api, "/api/learning/items", title="Book", kind="book", path_id=p["id"])
    await api.delete(f"/api/learning/paths/{p['id']}")
    assert (await api.get("/api/learning/milestones")).json() == []
    assert (await api.get("/api/learning/items")).json()[0]["id"] == it["id"]
    assert (await api.get("/api/learning/items")).json()[0]["path_id"] is None


async def test_item_progress_drives_status_and_dates(api: AsyncClient) -> None:
    it = await mk(api, "/api/learning/items", title="Day Zero to Zero Day", kind="book", progress_total=12)
    assert it["status"] == "backlog" and it["percent"] == 0
    r = (await api.patch(f"/api/learning/items/{it['id']}", json={"progress_current": 3})).json()
    assert r["status"] == "in_progress" and r["started"] == TODAY.isoformat() and r["percent"] == 25
    r = (await api.patch(f"/api/learning/items/{it['id']}", json={"progress_current": 12})).json()
    assert r["status"] == "done" and r["finished"] == TODAY.isoformat() and r["percent"] == 100


async def test_dropped_item_is_not_revived_by_progress(api: AsyncClient) -> None:
    it = await mk(api, "/api/learning/items", title="Meh", kind="article", status="dropped")
    r = (await api.patch(f"/api/learning/items/{it['id']}", json={"progress_current": 5})).json()
    assert r["status"] == "dropped"


async def test_items_cover_books_articles_and_writing_with_filters(api: AsyncClient) -> None:
    for kind in ("book", "article", "writing", "course", "lab", "video", "paper", "other"):
        await mk(api, "/api/learning/items", title=f"a {kind}", kind=kind)
    assert (await api.post("/api/learning/items", json={"title": "x", "kind": "podcast"})).status_code == 422
    assert len((await api.get("/api/learning/items")).json()) == 8
    assert [i["kind"] for i in (await api.get("/api/learning/items?kind=writing")).json()] == ["writing"]
    assert (await api.get("/api/learning/items?status=done")).json() == []
    bad = await api.post("/api/learning/items", json={"title": "x", "kind": "book", "rating": 9})
    assert bad.status_code == 422
    bad = await api.post("/api/learning/items", json={"title": "x", "kind": "book", "url": "javascript:alert(1)"})
    assert bad.status_code == 422  # only http(s) links are stored


async def test_learning_overview_counts(api: AsyncClient) -> None:
    await mk(api, "/api/learning/items", title="b1", kind="book", status="done")
    await mk(api, "/api/learning/items", title="b2", kind="book", status="in_progress")
    await mk(api, "/api/learning/items", title="w1", kind="writing", status="done")
    o = (await api.get("/api/learning/overview")).json()
    assert o["done_by_kind"] == {"book": 1, "writing": 1}
    assert o["in_progress"] == 1


# --- trips -------------------------------------------------------------------------------------
async def test_trip_with_items_budget_and_countdown(api: AsyncClient) -> None:
    t = await mk(api, "/api/trips", destination="Morocco", start=iso(20), end=iso(30), status="planned", budget="1000")
    await mk(api, f"/api/trips/{t['id']}/items", kind="flight", label="Paris-Marrakech", cost="300", done=True)
    await mk(api, f"/api/trips/{t['id']}/items", kind="todo", label="Renew passport")
    got = (await api.get("/api/trips")).json()[0]
    assert got["spent"] == "300.00" and got["budget_left"] == "700.00"
    assert got["days_until"] == 20 and got["items_total"] == 2 and got["items_done"] == 1
    detail = (await api.get(f"/api/trips/{t['id']}")).json()
    assert [i["label"] for i in detail["items"]] == ["Paris-Marrakech", "Renew passport"]


async def test_trip_validation(api: AsyncClient) -> None:
    r = await api.post("/api/trips", json={"destination": "X", "start": iso(5), "end": iso(1)})
    assert r.status_code == 422
    assert (await api.post("/api/trips", json={"destination": "X", "status": "maybe"})).status_code == 422
    t = await mk(api, "/api/trips", destination="Bali")  # dates optional for an idea
    assert t["status"] == "idea" and t["start"] is None
    r = await api.patch(f"/api/trips/{t['id']}", json={"start": iso(9), "end": iso(2)})
    assert r.status_code == 422


async def test_trips_sorted_upcoming_first_and_delete_cascades(api: AsyncClient) -> None:
    late = await mk(api, "/api/trips", destination="Late", start=iso(90))
    soon = await mk(api, "/api/trips", destination="Soon", start=iso(10))
    idea = await mk(api, "/api/trips", destination="Idea")
    assert [t["destination"] for t in (await api.get("/api/trips")).json()] == ["Soon", "Late", "Idea"]
    await mk(api, f"/api/trips/{soon['id']}/items", kind="stay", label="Hotel")
    await api.delete(f"/api/trips/{soon['id']}")
    assert (await api.get(f"/api/trips/{soon['id']}")).status_code == 404
    assert late and idea


# --- goals -------------------------------------------------------------------------------------
async def test_goal_status_and_progress(api: AsyncClient) -> None:
    g = await mk(api, "/api/goals", title="PortSwigger labs", unit="labs", target="60", current="30", start=iso(-90), deadline=iso(90))
    assert g["progress"] == 0.5 and g["status"] == "on_track"
    behind = await mk(api, "/api/goals", title="Posts", target="8", current="0", start=iso(-90), deadline=iso(90))
    assert behind["status"] == "behind"
    new = await mk(api, "/api/goals", title="New", target="8", start=iso(-2), deadline=iso(90))
    assert new["status"] == "starting"
    done = (await api.patch(f"/api/goals/{g['id']}", json={"current": "60"})).json()
    assert done["status"] == "done"
    assert (await api.post("/api/goals", json={"title": "x", "target": "0", "start": iso(0), "deadline": iso(5)})).status_code == 422
    assert (await api.post("/api/goals", json={"title": "x", "target": "5", "start": iso(5), "deadline": iso(0)})).status_code == 422


# --- weekly check ------------------------------------------------------------------------------
MONDAY = (TODAY - timedelta(days=TODAY.weekday())).isoformat()


async def test_weekly_metrics_and_check_scoring(api: AsyncClient) -> None:
    focus = await mk(api, "/api/weekly/metrics", name="Focus hours", unit="h", target="16", min_viable="5")
    sport = await mk(api, "/api/weekly/metrics", name="Sport", unit="sessions", target="5", min_viable="2")
    r = await api.put(f"/api/weekly/checks/{MONDAY}", json={
        "energy": 4, "win": "Shipped post", "blocker": "", "focus_next": "Pivoting",
        "values": {focus["id"]: "8", sport["id"]: "5"},
    })
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["score"] == 0.75 and c["min_viable"] is True and c["burnout"] is False
    assert c["values"][focus["id"]] == "8.00"
    # idempotent upsert: same week again replaces values, no duplicate row
    r2 = await api.put(f"/api/weekly/checks/{MONDAY}", json={"energy": 1, "values": {focus["id"]: "2"}})
    assert r2.json()["burnout"] is True and r2.json()["min_viable"] is False
    assert len((await api.get("/api/weekly/checks")).json()) == 1


async def test_weekly_validation(api: AsyncClient) -> None:
    m = await mk(api, "/api/weekly/metrics", name="Sleep", unit="h", target="7.5")
    tuesday = (TODAY - timedelta(days=TODAY.weekday()) + timedelta(days=1)).isoformat()
    assert (await api.put(f"/api/weekly/checks/{tuesday}", json={"values": {}})).status_code == 422
    assert (await api.put(f"/api/weekly/checks/{MONDAY}", json={"energy": 9, "values": {}})).status_code == 422
    unknown = "00000000-0000-0000-0000-000000000000"
    assert (await api.put(f"/api/weekly/checks/{MONDAY}", json={"values": {unknown: "1"}})).status_code == 422
    assert (await api.put(f"/api/weekly/checks/{MONDAY}", json={"values": {m["id"]: "-1"}})).status_code == 422


async def test_weekly_summary_averages_and_consistency(api: AsyncClient) -> None:
    m = await mk(api, "/api/weekly/metrics", name="Focus", unit="h", target="16", min_viable="5")
    for weeks_ago, v in ((1, "16"), (2, "13"), (3, "2")):
        monday = (TODAY - timedelta(days=TODAY.weekday()) - timedelta(weeks=weeks_ago)).isoformat()
        await api.put(f"/api/weekly/checks/{monday}", json={"focus_next": f"w{weeks_ago}", "values": {m["id"]: v}})
    s = (await api.get("/api/weekly/summary")).json()
    assert s["weeks_logged"] == 3
    assert s["consistency"] == round(2 / 3, 4)
    row = s["metrics"][0]
    assert row["average"] == "10.33" or row["average"].startswith("10.3")
    assert row["status"] == "below"
    assert s["last"]["focus_next"] == "w1"


async def test_deleting_a_metric_drops_its_values(api: AsyncClient) -> None:
    m = await mk(api, "/api/weekly/metrics", name="Steps", unit="", target="10000")
    await api.put(f"/api/weekly/checks/{MONDAY}", json={"values": {m["id"]: "5000"}})
    await api.delete(f"/api/weekly/metrics/{m['id']}")
    assert (await api.get("/api/weekly/checks")).json()[0]["values"] == {}


# --- cross-cutting -----------------------------------------------------------------------------
async def test_new_modules_require_login(anon: AsyncClient) -> None:
    for p in ("/api/learning/paths", "/api/learning/items", "/api/learning/overview", "/api/trips",
              "/api/goals", "/api/weekly/metrics", "/api/weekly/checks", "/api/weekly/summary"):
        assert (await anon.get(p)).status_code == 401, p


async def test_search_finds_new_content(api: AsyncClient) -> None:
    await mk(api, "/api/learning/paths", name="Quokka path", kind="main")
    await mk(api, "/api/learning/items", title="Quokka handbook", kind="book")
    await mk(api, "/api/trips", destination="Quokka island")
    await mk(api, "/api/goals", title="Quokka goal", target="1", start=iso(0), deadline=iso(9))
    kinds = {h["kind"] for h in (await api.get("/api/search?q=quokka")).json()}
    assert {"path", "item", "trip", "goal"} <= kinds


async def test_backup_roundtrip_includes_life_data_and_old_backups_still_load(api: AsyncClient) -> None:
    p = await mk(api, "/api/learning/paths", name="CPTS", kind="main")
    await mk(api, f"/api/learning/paths/{p['id']}/milestones", title="m", horizon="weekly")
    await mk(api, "/api/learning/items", title="Book", kind="book", path_id=p["id"])
    t = await mk(api, "/api/trips", destination="Morocco", budget="500")
    await mk(api, f"/api/trips/{t['id']}/items", kind="flight", label="f", cost="10")
    await mk(api, "/api/goals", title="g", target="5", start=iso(-5), deadline=iso(50))
    m = await mk(api, "/api/weekly/metrics", name="Focus", unit="h", target="16")
    await api.put(f"/api/weekly/checks/{MONDAY}", json={"win": "ok", "values": {m["id"]: "9"}})
    snap = (await api.get("/api/backup")).json()
    for key in ("paths", "milestones", "learning_items", "trips", "trip_items", "goals", "metrics", "week_checks"):
        assert len(snap[key]) == 1, key
    await api.delete(f"/api/trips/{t['id']}")
    await mk(api, "/api/goals", title="extra", target="5", start=iso(-5), deadline=iso(50))
    r = await api.post("/api/backup", json=snap)
    assert r.status_code == 204, r.text
    assert (await api.get("/api/backup")).json() == snap
    assert len((await api.get("/api/trips")).json()) == 1 and len((await api.get("/api/goals")).json()) == 1
    legacy = {k: v for k, v in snap.items() if k in {"version", "profile", "clients", "projects", "notes", "tasks", "entries", "recurring"}}
    assert (await api.post("/api/backup", json=legacy)).status_code == 204
    assert (await api.get("/api/trips")).json() == []  # a legacy backup replaces everything, life data included


async def test_backup_with_dangling_life_reference_is_rejected(api: AsyncClient) -> None:
    snap = (await api.get("/api/backup")).json()
    ghost = "22222222-2222-2222-2222-222222222222"
    snap["milestones"] = [{"id": "11111111-1111-1111-1111-111111111111", "path_id": ghost, "title": "x", "horizon": "weekly",
                           "due": None, "status": "todo", "notes": "", "created_at": "2026-01-01T00:00:00Z"}]
    assert (await api.post("/api/backup", json=snap)).status_code == 422


async def test_item_created_as_done_gets_dates_and_counts_this_year(api: AsyncClient) -> None:
    it = await mk(api, "/api/learning/items", title="Already read", kind="article", status="done")
    assert it["finished"] == TODAY.isoformat() and it["started"] == TODAY.isoformat()
    assert (await api.get("/api/learning/overview")).json()["done_this_year"] == 1
    explicit = await mk(api, "/api/learning/items", title="Old", kind="book", status="done", finished="2025-01-02")
    assert explicit["finished"] == "2025-01-02"


async def test_item_created_with_progress_starts_in_progress(api: AsyncClient) -> None:
    it = await mk(api, "/api/learning/items", title="Dante", kind="lab", progress_total=27, progress_current=9)
    assert it["status"] == "in_progress" and it["started"] == TODAY.isoformat()
    full = await mk(api, "/api/learning/items", title="Done lab", kind="lab", progress_total=3, progress_current=3)
    assert full["status"] == "done" and full["finished"] == TODAY.isoformat()
    explicit = await mk(api, "/api/learning/items", title="Parked", kind="lab", progress_total=3, progress_current=1, status="backlog")
    assert explicit["status"] == "backlog"  # an explicit status always wins on create
