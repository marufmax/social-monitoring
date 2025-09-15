"""
Unit of Work with workspace repository
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.database import get_async_session
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
import structlog

logger = structlog.get_logger()


class AbstractUnitOfWork(ABC):
    """Abstract Unit of Work interface"""

    users: UserRepository
    workspaces: WorkspaceRepository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.close()

    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass

    @abstractmethod
    async def close(self):
        pass


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """SQLAlchemy implementation of Unit of Work"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        self.users = UserRepository(self.session)
        self.workspaces = WorkspaceRepository(self.session)
        return await super().__aenter__()

    async def commit(self):
        await self.session.commit()
        logger.debug("Transaction committed")

    async def rollback(self):
        await self.session.rollback()
        logger.debug("Transaction rolled back")

    async def close(self):
        await self.session.close()


async def get_unit_of_work(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[AbstractUnitOfWork, None]:
    """Get Unit of Work instance as async context manager"""
    uow = SqlAlchemyUnitOfWork(session)
    async with uow:
        yield uow


async def get_unit_of_work_dependency(
    session: AsyncSession = Depends(get_async_session),
) -> AbstractUnitOfWork:
    """
    FastAPI dependency for Unit of Work
    Use this with Depends() in your route handlers
    """
    return SqlAlchemyUnitOfWork(session)
