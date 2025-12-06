from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

__all__ = ["DATABASE_URL", "engine", "Base", "SessionLocal"]

## SQLite database URL
DATABASE_URL = "sqlite:///farmrpg_market_prices.db"

## Create engine
engine = create_engine(DATABASE_URL, echo=False, future=True)

## Create all tables
Base.metadata.create_all(engine)

## Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
