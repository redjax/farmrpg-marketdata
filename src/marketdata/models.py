from marketdata.db import Base

from sqlalchemy import Integer, String, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

__all__ = [
    "SteakPriceModel",
    "KebabPriceModel",
    "SteakPriceCurrent",
    "KabobPriceCurrent",
]


class SteakPriceModel(Base):
    __tablename__ = "steak_prices"
    __table_args__ = (UniqueConstraint("date", name="uq_steak_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)


class KebabPriceModel(Base):
    __tablename__ = "kebab_prices"
    __table_args__ = (UniqueConstraint("timestamp", name="uq_kebab_timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)


class SteakPriceCurrentModel(Base):
    __tablename__ = "steak_prices_current"
    __table_args__ = (UniqueConstraint("id", name="uq_steak_current"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)


class KebabPriceCurrentModel(Base):
    __tablename__ = "kebab_prices_current"
    __table_args__ = (UniqueConstraint("id", name="uq_kebab_current"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
