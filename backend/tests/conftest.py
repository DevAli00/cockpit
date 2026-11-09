import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.services.users import ensure_owner

EMAIL = "owner@example.test"
PASSWORD = "test-password-123"  # test-only value, never used outside the test DB


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite://",
        secret_key="s" * 48,
        admin_email=EMAIL,
        admin_password=PASSWORD,
        cookie_secure=False,
    )


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    # Set COCKPIT_TEST_DATABASE_URL to a throwaway Postgres to run the suite against the real thing.
    pg_url = os.environ.get("COCKPIT_TEST_DATABASE_URL")
    if pg_url:
        eng = create_async_engine(pg_url)
    else:
        eng = create_async_engine(
            "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        )

        @event.listens_for(eng.sync_engine, "connect")
        def _fk_on(dbapi_conn, _):  # type: ignore[no-untyped-def]
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    if pg_url:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def anon(settings: Settings, engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    app = create_app(settings, engine=engine)
    async with app.state.session_factory() as s:
        await ensure_owner(s, settings.admin_email, settings.admin_password)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def api(anon: AsyncClient) -> AsyncClient:
    r = await anon.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return anon
