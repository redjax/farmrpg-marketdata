import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from marketdata.db.base import Base

DB_FILENAME = "farmrpg_market_prices.db"
DATABASE_URL = f"sqlite:///{DB_FILENAME}"

# Session factory
SessionLocal = sessionmaker(
    bind=create_engine(DATABASE_URL, future=True),
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_engine():
    """Return a SQLAlchemy engine for the database."""
    ## Ensure DB directory exists
    Path(str(DB_FILENAME)).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(DATABASE_URL, future=True)
    return engine


@contextmanager
def get_session():
    """Provide a transactional scope around a series of operations."""
    engine = get_engine()
    session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize the database, creating tables if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(engine)

    return engine
