from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(AsyncAttrs, DeclarativeBase):
    pass
