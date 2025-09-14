"""
Updated Unit of Work with workspace repository
"""
from abc import ABC, abstractmethod
from typing import AsyncContextManager
from sqlalchemy.ext.asyncio import AsyncSession
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

async def get_unit_of_work() -> AsyncContextManager[AbstractUnitOfWork]:
    """Get Unit of Work instance"""
    async with get_async_session() as session:
        yield SqlAlchemyUnitOfWork(session)

