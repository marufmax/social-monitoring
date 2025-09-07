from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings
from sqlalchemy.pool import NullPool

ASYNC_DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
SYNC_DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+syncpg://")

async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    poolclass=NullPool if settings.TESTING else None,
)

sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

SessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def get_sync_session():
    """Dependency for getting sync database session. Mostly for migrations and scripts"""
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise

@event.listens_for(sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set PostgreSQL connection parameters for performance."""
    if 'postgresql' in str(sync_engine.url):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'UTC'")
            cursor.execute("SET statement_timeout = '30s'")
            cursor.execute("SET lock_timeout = '10s'")


@event.listens_for(async_engine.sync_engine, "connect")
def set_async_sqlite_pragma(dbapi_connection, connection_record):
    """Set PostgreSQL connection parameters for async performance."""
    if 'postgresql' in str(async_engine.url):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'UTC'")
            cursor.execute("SET statement_timeout = '30s'")
            cursor.execute("SET lock_timeout = '10s'")