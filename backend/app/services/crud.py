from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.services.errors import InvalidError, NotFoundError

M = TypeVar("M", bound=Base)


async def get_or_404(s: AsyncSession, model: type[M], id_: uuid.UUID) -> M:
    obj = await s.get(model, id_)
    if obj is None:
        raise NotFoundError(f"{model.__name__} not found")
    return obj


async def list_all(s: AsyncSession, model: type[M], *order: Any) -> list[M]:
    return list((await s.scalars(select(model).order_by(*order))).all())


async def _commit(s: AsyncSession) -> None:
    try:
        await s.commit()
    except IntegrityError as exc:
        await s.rollback()
        raise InvalidError("references a record that does not exist") from exc


async def create(s: AsyncSession, model: type[M], data: Mapping[str, Any]) -> M:
    obj = model(**data)
    s.add(obj)
    await _commit(s)
    await s.refresh(obj)  # return what the database stored (e.g. rounded amounts)
    return obj


async def update(s: AsyncSession, obj: M, data: Mapping[str, Any]) -> M:
    for key, value in data.items():
        setattr(obj, key, value)
    await _commit(s)
    await s.refresh(obj)
    return obj


async def delete(s: AsyncSession, obj: Base) -> None:
    await s.delete(obj)
    await s.commit()
