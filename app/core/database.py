import os
import pkgutil
import importlib
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_timeout=30,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def import_all_models():
    """Dynamically import all model files across all module directories to register on Base.metadata."""
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
                        logger.debug(f"Skipping model import {pkg_name}.{mod_name}: {e}")
