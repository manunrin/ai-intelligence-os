"""SQLAlchemy ORM base."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

constraint_naming_convention = {
    "ck": "%(table_name)s_%(constraint_name)s",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "%(table_name)s_%(column_0_name)s_uq",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData()


class Base(DeclarativeBase):
    pass


def _utcnow():
    """Return a timezone-aware UTC datetime default."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)
