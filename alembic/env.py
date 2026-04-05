from logging.config import fileConfig
import logging
import os

from sqlalchemy import engine_from_config, create_engine, text
from sqlalchemy import pool
from sqlalchemy.exc import SQLAlchemyError

from alembic import context
from dotenv import load_dotenv

from db.database import Base
from db import models  # noqa: F401
target_metadata = Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

load_dotenv()
logger = logging.getLogger("alembic.env")


def _build_connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "3"))
    return {"connect_timeout": connect_timeout}


def _can_connect(url: str) -> bool:
    try:
        test_engine = create_engine(
            url,
            future=True,
            pool_pre_ping=True,
            connect_args=_build_connect_args(url),
        )
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.warning("Alembic DB connectivity check failed for %s: %s", url, exc)
        return False


def _resolve_migration_db_url() -> str:
    primary_url = os.getenv("PRIMARY_DATABASE_URL") or os.getenv("DATABASE_URL")
    fallback_url = os.getenv("FALLBACK_DATABASE_URL", "sqlite:///./app.db")
    failover_enabled = os.getenv("DB_FAILOVER_ENABLED", "true").lower() == "true"

    if primary_url and failover_enabled and primary_url != fallback_url:
        if _can_connect(primary_url):
            return primary_url
        logger.warning("Alembic falling back to local DB for migrations: %s", fallback_url)
        return fallback_url

    return primary_url or fallback_url

db_url = _resolve_migration_db_url()
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
