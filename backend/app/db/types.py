from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Always tz-aware UTC in Python, regardless of whether the backend keeps the zone."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):  # type: ignore[no-untyped-def]
        if value is not None and value.tzinfo is None:
            raise ValueError("naive datetime not allowed")
        return value.astimezone(UTC) if value is not None else None

    def process_result_value(self, value: datetime | None, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
