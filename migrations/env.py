import asyncio
import os
import sys
import importlib
import pkgutil
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine

from alembic import context

# ── Append app root to sys.path ──────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def load_all_models():
    """Explicitly & dynamically imports all ORM model modules across all app domains."""
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
    root_dir = os.path.dirname(app_dir)

    for root, dirs, files in os.walk(app_dir):
        if os.path.basename(root) == "models":
            rel_path = os.path.relpath(root, root_dir)
            pkg_name = rel_path.replace(os.sep, ".").replace("/", ".")
            for _, mod_name, _ in pkgutil.iter_modules([root]):
                if not mod_name.startswith("__"):
                    try:
                        importlib.import_module(f"{pkg_name}.{mod_name}")
                    except Exception as e:
                        print(f"Warning importing {pkg_name}.{mod_name}: {e}")


# Load all models into Base.metadata
load_all_models()

target_metadata = Base.metadata

# Override URL dynamically with application settings
db_url = settings.DATABASE_URL
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)


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
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
