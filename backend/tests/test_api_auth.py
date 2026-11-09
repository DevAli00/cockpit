from httpx import AsyncClient

from tests.conftest import EMAIL, PASSWORD


async def test_protected_routes_require_login(anon: AsyncClient) -> None:
    for path in ("/api/clients", "/api/tasks", "/api/projects", "/api/finance/summary", "/api/me"):
        assert (await anon.get(path)).status_code == 401, path


async def test_health_is_public(anon: AsyncClient) -> None:
    assert (await anon.get("/api/health")).json() == {"status": "ok"}


async def test_login_sets_httponly_cookie_and_me_works(anon: AsyncClient) -> None:
    r = await anon.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert (await anon.get("/api/me")).json()["email"] == EMAIL


async def test_wrong_password_and_unknown_user_give_same_error(anon: AsyncClient) -> None:
    a = await anon.post("/api/auth/login", json={"email": EMAIL, "password": "nope"})
    b = await anon.post("/api/auth/login", json={"email": "who@example.test", "password": "nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


async def test_logout_clears_session(api: AsyncClient) -> None:
    assert (await api.post("/api/auth/logout")).status_code == 204
    api.cookies.clear()
    assert (await api.get("/api/me")).status_code == 401


async def test_login_is_rate_limited(anon: AsyncClient) -> None:
    codes = [
        (await anon.post("/api/auth/login", json={"email": EMAIL, "password": "bad"})).status_code
        for _ in range(8)
    ]
    assert 429 in codes
    # even the right password is refused while locked out
    ok = await anon.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert ok.status_code == 429


async def test_tampered_cookie_rejected(anon: AsyncClient) -> None:
    anon.cookies.set("cockpit_session", "garbage.token.value")
    assert (await anon.get("/api/me")).status_code == 401


async def test_security_headers(anon: AsyncClient) -> None:
    r = await anon.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
