import os
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PRIMARY_DATABASE_URL = os.getenv("PRIMARY_DATABASE_URL") or os.getenv("DATABASE_URL", "sqlite:///./app.db")
FALLBACK_DATABASE_URL = os.getenv("FALLBACK_DATABASE_URL", "sqlite:///./app.db")
DB_FAILOVER_ENABLED = os.getenv("DB_FAILOVER_ENABLED", "true").lower() == "true"
DB_CONNECT_TIMEOUT_SECONDS = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "3"))


def _build_connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS}


def _make_engine(url: str):
    return create_engine(
        url,
        future=True,
        pool_pre_ping=True,
        connect_args=_build_connect_args(url),
    )


def _try_make_engine(url: str):
    try:
        return _make_engine(url)
    except Exception as exc:
        logger.warning("Database engine creation failed for %s: %s", url, exc)
        return None


def _can_connect(test_engine) -> bool:
    try:
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.warning("Database connection check failed for %s: %s", test_engine.url, exc)
        return False


ACTIVE_DATABASE_URL = PRIMARY_DATABASE_URL

if DB_FAILOVER_ENABLED and PRIMARY_DATABASE_URL != FALLBACK_DATABASE_URL:
    primary_engine = _try_make_engine(PRIMARY_DATABASE_URL)
    if primary_engine and _can_connect(primary_engine):
        engine = primary_engine
    else:
        logger.warning("Falling back to local database: %s", FALLBACK_DATABASE_URL)
        ACTIVE_DATABASE_URL = FALLBACK_DATABASE_URL
        fallback_engine = _try_make_engine(FALLBACK_DATABASE_URL)
        if fallback_engine is None:
            raise RuntimeError("Fallback database engine could not be created")
        engine = fallback_engine
else:
    single_engine = _try_make_engine(PRIMARY_DATABASE_URL)
    if single_engine is None:
        raise RuntimeError("Primary database engine could not be created")
    engine = single_engine

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass