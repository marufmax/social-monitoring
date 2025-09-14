"""
Async user repository implementation
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.user import AppUser
from app.core.exceptions import ResourceNotFoundError
import structlog

logger = structlog.get_logger()


class UserRepository:
    """Async user repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, user_id: str, load_workspaces: bool = False
    ) -> Optional[AppUser]:
        """Get user by ID with optional workspace loading"""
        try:
            stmt = select(AppUser).where(AppUser.user_id == user_id)

            if load_workspaces:
                stmt = stmt.options(selectinload(AppUser.workspace_memberships))

            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error("Failed to get user by ID", user_id=user_id, error=str(e))
            raise

    async def get_by_email(self, email: str) -> Optional[AppUser]:
        """Get user by email (requires joining with supertokens_users)"""
        try:
            # In a real implementation, you'd join with supertokens_users
            # For now, this is a placeholder
            stmt = select(AppUser).where(AppUser.user_id.like(f"%{email}%"))
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error("Failed to get user by email", email=email, error=str(e))
            raise

    async def create(self, user_data: Dict[str, Any]) -> AppUser:
        """Create new user - NO COMMIT (handled by UoW)"""
        try:
            user = AppUser(**user_data)
            self.session.add(user)
            await self.session.flush()  # Get ID without committing
            await self.session.refresh(user)

            logger.info("User created in transaction", user_id=user.user_id)
            return user

        except Exception as e:
            logger.error("Failed to create user", error=str(e))
            raise

    async def update(
        self, user_id: str, update_data: Dict[str, Any]
    ) -> Optional[AppUser]:
        """Update user - NO COMMIT (handled by UoW)"""
        try:
            stmt = select(AppUser).where(AppUser.user_id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            await self.session.flush()
            await self.session.refresh(user)

            logger.info("User updated in transaction", user_id=user_id)
            return user

        except Exception as e:
            logger.error("Failed to update user", user_id=user_id, error=str(e))
            raise

    async def exists_by_id(self, user_id: str) -> bool:
        """Check if user exists by ID"""
        try:
            stmt = select(AppUser.user_id).where(AppUser.user_id == user_id).limit(1)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.error(
                "Failed to check user existence", user_id=user_id, error=str(e)
            )
            return False
