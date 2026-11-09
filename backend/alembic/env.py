import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import models  # noqa: F401  (registers tables on Base.metadata)
from app.db.base import Base

target_metadata = Base.metadata


def _url() -> str:
    url = os.environ.get("COCKPIT_DATABASE_URL")
    if not url:
        raise RuntimeError("COCKPIT_DATABASE_URL is not set")
    return url


def _run(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _main() -> None:
    engine = create_async_engine(_url())
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("offline mode is not supported")
asyncio.run(_main())
