from sqlalchemy import Integer, String, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

__all__ = ["Base"]


class Base(DeclarativeBase):
    pass
