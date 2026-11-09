"""Schema management for the standalone (SQLite) app, where Alembic is not available.

Creates missing tables and adds columns introduced by newer versions. Changes so far have only
ever been additive; anything else (renames, drops) would need a real migration.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Column, Connection, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import models  # noqa: F401  (registers tables on Base.metadata)
from app.db.base import Base

log = logging.getLogger("cockpit.schema")


@dataclass(frozen=True, slots=True)
class _Plan:
    tables: tuple[str, ...]
    columns: tuple[tuple[str, str], ...]  # (table, column)


def _plan(conn: Connection) -> _Plan:
    insp = inspect(conn)
    existing = set(insp.get_table_names())
    missing_tables = tuple(t.name for t in Base.metadata.sorted_tables if t.name not in existing)
    missing_columns = tuple(
        (t.name, c.name)
        for t in Base.metadata.sorted_tables
        if t.name in existing
        for c in t.columns
        if c.name not in {col["name"] for col in insp.get_columns(t.name)}
    )
    return _Plan(missing_tables, missing_columns)


def _literal(value: Any) -> str | None:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return None


def _default_sql(col: Column[Any], conn: Connection) -> str | None:
    if col.server_default is not None:
        arg = getattr(col.server_default, "arg", None)
        return _literal(arg) if isinstance(arg, str) else str(arg.compile(dialect=conn.dialect))  # type: ignore[union-attr]
    if col.default is not None and getattr(col.default, "is_scalar", False):
        return _literal(col.default.arg)  # type: ignore[attr-defined]
    return None


def _add_column_sql(col: Column[Any], conn: Connection) -> str:
    parts = [f'ALTER TABLE "{col.table.name}" ADD COLUMN "{col.name}" {col.type.compile(dialect=conn.dialect)}']
    default = _default_sql(col, conn)
    if default is not None:
        parts.append(f"DEFAULT {default}")
        if not col.nullable:
            parts.append("NOT NULL")  # only possible with a default: existing rows need a value
    for fk in col.foreign_keys:
        parts.append(f'REFERENCES "{fk.column.table.name}" ("{fk.column.name}")')
        if fk.ondelete:
            parts.append(f"ON DELETE {fk.ondelete}")
    return " ".join(parts)


def _apply(conn: Connection, plan: _Plan) -> None:
    Base.metadata.create_all(conn)
    for table, column in plan.columns:
        conn.execute(text(_add_column_sql(Base.metadata.tables[table].columns[column], conn)))


def _copy_before_upgrade(engine: AsyncEngine) -> None:
    """Keep a copy of an existing SQLite file before altering it."""
    path = engine.url.database
    if engine.dialect.name != "sqlite" or not path or not Path(path).is_file():
        return
    target = f"{path}.before-upgrade-{datetime.now():%Y%m%d-%H%M%S}"
    src, dst = sqlite3.connect(path), sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    log.info("copied database to %s before upgrading", target)


async def ensure_schema(engine: AsyncEngine) -> list[str]:
    """Bring the database up to the current models. Returns what was done (empty when up to date)."""
    async with engine.connect() as conn:
        plan = await conn.run_sync(_plan)
    if not plan.tables and not plan.columns:
        return []
    if plan.columns:
        _copy_before_upgrade(engine)
    async with engine.begin() as conn:
        await conn.run_sync(_apply, plan)
    changes = [f"create table {t}" for t in plan.tables] + [f"add column {t}.{c}" for t, c in plan.columns]
    log.info("schema updated: %s", ", ".join(changes))
    return changes
