"""SQLAlchemy ORM base."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

metadata = MetaData(name="ai_intelligence_os")


class Base(DeclarativeBase):
    pass
