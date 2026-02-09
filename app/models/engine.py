from collections.abc import AsyncGenerator

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from configs import app_config


engine = create_async_engine(
    str(app_config.SQLALCHEMY_DATABASE_URI),
    **app_config.SQLALCHEMY_ENGINE_OPTIONS,
)

# Configure session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Engine for Celery tasks — NullPool avoids event loop binding issues
_task_engine = create_async_engine(
    str(app_config.SQLALCHEMY_DATABASE_URI),
    poolclass=NullPool,
)

TaskSessionLocal = async_sessionmaker(
    _task_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def run_async(coro):
    """Run an async coroutine in Celery worker context (prefork pool)."""
    import asyncio
    return asyncio.run(coro)


# Dependency injection function
async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Universal index naming convention (applicable to all databases)
INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData(naming_convention=INDEXES_NAMING_CONVENTION)


__all__ = [
    "AsyncSession",
    "AsyncSessionLocal",
    "TaskSessionLocal",
    "engine",
    "get_db",
    "metadata",
]
