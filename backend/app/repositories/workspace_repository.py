"""
async workspace repository
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, exists
from sqlalchemy.orm import selectinload
from app.models.workspace import WorkspaceMember
from app.models.workspace import Workspace
import structlog

logger = structlog.get_logger()


class WorkspaceRepository:
    """Extended async workspace repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, workspace_data: Dict[str, Any]) -> Workspace:
        """Create workspace - NO COMMIT (handled by UoW)"""
        try:
            workspace = Workspace(**workspace_data)
            self.session.add(workspace)
            await self.session.flush()
            await self.session.refresh(workspace)

            logger.info("Workspace created in transaction", workspace_id=workspace.id)
            return workspace

        except Exception as e:
            logger.error("Failed to create workspace", error=str(e))
            raise

    async def get_by_id(
        self, workspace_id: str, load_members: bool = False
    ) -> Optional[Workspace]:
        """Get workspace by ID"""
        try:
            stmt = select(Workspace).where(Workspace.id == workspace_id)

            if load_members:
                stmt = stmt.options(selectinload(Workspace.members))

            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get workspace", workspace_id=workspace_id, error=str(e)
            )
            raise

    async def get_by_slug(self, slug: str) -> Optional[Workspace]:
        """Get workspace by slug"""
        try:
            stmt = select(Workspace).where(Workspace.slug == slug)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error("Failed to get workspace by slug", slug=slug, error=str(e))
            raise

    async def slug_exists(self, slug: str) -> bool:
        """Check if workspace slug exists"""
        try:
            stmt = select(exists().where(Workspace.slug == slug))
            result = await self.session.execute(stmt)
            return result.scalar()

        except Exception as e:
            logger.error("Failed to check slug existence", slug=slug, error=str(e))
            return True  # Err on the side of caution

    async def get_user_memberships(
        self, user_id: str, load_workspaces: bool = True
    ) -> List[WorkspaceMember]:
        """Get user's workspace memberships"""
        try:
            stmt = select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)

            if load_workspaces:
                stmt = stmt.options(selectinload(WorkspaceMember.workspace))

            result = await self.session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(
                "Failed to get user memberships", user_id=user_id, error=str(e)
            )
            raise

    async def get_workspace_members(
        self,
        workspace_id: str,
        skip: int = 0,
        limit: int = 100,
        load_users: bool = True,
    ) -> List[WorkspaceMember]:
        """Get workspace members with pagination"""
        try:
            stmt = (
                select(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == workspace_id)
                .offset(skip)
                .limit(limit)
            )

            if load_users:
                stmt = stmt.options(selectinload(WorkspaceMember.user))

            result = await self.session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(
                "Failed to get workspace members",
                workspace_id=workspace_id,
                error=str(e),
            )
            raise

    async def create_membership(
        self, membership_data: Dict[str, Any]
    ) -> WorkspaceMember:
        """Create workspace membership - NO COMMIT (handled by UoW)"""
        try:
            membership = WorkspaceMember(**membership_data)
            self.session.add(membership)
            await self.session.flush()
            await self.session.refresh(membership)

            logger.info(
                "Workspace membership created",
                workspace_id=membership.workspace_id,
                user_id=membership.user_id,
                role=membership.role,
            )
            return membership

        except Exception as e:
            logger.error("Failed to create membership", error=str(e))
            raise

    async def update_membership(
        self, membership_id: str, update_data: Dict[str, Any]
    ) -> Optional[WorkspaceMember]:
        """Update workspace membership - NO COMMIT (handled by UoW)"""
        try:
            stmt = select(WorkspaceMember).where(WorkspaceMember.id == membership_id)
            result = await self.session.execute(stmt)
            membership = result.scalar_one_or_none()

            if not membership:
                return None

            for key, value in update_data.items():
                if hasattr(membership, key):
                    setattr(membership, key, value)

            await self.session.flush()
            await self.session.refresh(membership)

            logger.info("Workspace membership updated", membership_id=membership_id)
            return membership

        except Exception as e:
            logger.error(
                "Failed to update membership", membership_id=membership_id, error=str(e)
            )
            raise

    async def delete_membership(self, membership_id: str) -> bool:
        """Delete workspace membership - NO COMMIT (handled by UoW)"""
        try:
            stmt = select(WorkspaceMember).where(WorkspaceMember.id == membership_id)
            result = await self.session.execute(stmt)
            membership = result.scalar_one_or_none()

            if not membership:
                return False

            await self.session.delete(membership)
            await self.session.flush()

            logger.info("Workspace membership deleted", membership_id=membership_id)
            return True

        except Exception as e:
            logger.error(
                "Failed to delete membership", membership_id=membership_id, error=str(e)
            )
            raise

    async def get_membership_by_user_and_workspace(
        self, user_id: str, workspace_id: str
    ) -> Optional[WorkspaceMember]:
        """Get specific membership by user and workspace"""
        try:
            stmt = select(WorkspaceMember).where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error("Failed to get membership",
                         user_id=user_id, workspace_id=workspace_id, error=str(e))
            raise
