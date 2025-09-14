"""
Async workspace service with proper transaction management
"""

from typing import List, Dict, Any, Optional
from app.core.unit_of_work import AbstractUnitOfWork
from app.models.workspace import WorkspaceRole
from app.core.exceptions import WorkspaceError, AuthorizationError
import structlog
import uuid
from app.core.utils import slugify

logger = structlog.get_logger()


class WorkspaceService:
    """Async workspace service"""

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def create_workspace(
        self, workspace_data: Dict[str, Any], created_by: str
    ) -> Dict[str, Any]:
        """Create a new workspace with owner membership"""
        try:
            # Generate unique slug
            base_slug = slugify(workspace_data["name"])
            slug = await self._generate_unique_slug(base_slug)

            # Create workspace
            workspace_id = str(uuid.uuid4())
            workspace = await self.uow.workspaces.create(
                {
                    "id": workspace_id,
                    "name": workspace_data["name"],
                    "slug": slug,
                    "description": workspace_data.get("description"),
                    "settings": workspace_data.get("settings", {}),
                    "created_by": created_by,
                }
            )

            # Create owner membership
            await self.uow.workspaces.create_membership(
                {
                    "workspace_id": workspace_id,
                    "user_id": created_by,
                    "role": WorkspaceRole.OWNER,
                    "permissions": self._get_owner_permissions(),
                }
            )

            logger.info(
                "Workspace created", workspace_id=workspace_id, created_by=created_by
            )

            return {
                "id": workspace_id,
                "name": workspace.name,
                "slug": workspace.slug,
                "description": workspace.description,
                "settings": workspace.settings,
                "created_by": created_by,
                "created_at": workspace.created_at.isoformat(),
            }

        except Exception as e:
            logger.error("Failed to create workspace", error=str(e))
            raise WorkspaceError("Failed to create workspace")

    async def get_user_workspaces(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all workspaces for a user"""
        try:
            memberships = await self.uow.workspaces.get_user_memberships(
                user_id, load_workspaces=True
            )

            workspaces = []
            for membership in memberships:
                if membership.workspace:
                    workspaces.append(
                        {
                            "id": str(membership.workspace_id),
                            "name": membership.workspace.name,
                            "slug": membership.workspace.slug,
                            "description": membership.workspace.description,
                            "settings": membership.workspace.settings,
                            "created_by": membership.workspace.created_by,
                            "created_at": membership.workspace.created_at.isoformat(),
                            "user_role": membership.role.value
                            if hasattr(membership.role, "value")
                            else membership.role,
                            "joined_at": membership.joined_at.isoformat(),
                        }
                    )

            return workspaces

        except Exception as e:
            logger.error("Failed to get user workspaces", user_id=user_id, error=str(e))
            raise WorkspaceError("Failed to retrieve workspaces")

    async def check_user_access(self, user_id: str, workspace_id: str) -> bool:
        """Check if user has access to workspace"""
        try:
            memberships = await self.uow.workspaces.get_user_memberships(user_id)
            return any(
                str(membership.workspace_id) == workspace_id
                for membership in memberships
            )
        except Exception:
            return False

    async def get_workspace_members(
        self, workspace_id: str, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get workspace members"""
        try:
            members = await self.uow.workspaces.get_workspace_members(
                workspace_id, skip=skip, limit=limit
            )

            return [
                {
                    "user_id": member.user_id,
                    "role": member.role.value
                    if hasattr(member.role, "value")
                    else member.role,
                    "permissions": member.permissions,
                    "joined_at": member.joined_at.isoformat(),
                    "user": {
                        "name": member.user.name if member.user else None,
                        "display_name": member.user.display_name
                        if member.user
                        else None,
                        "email": None,  # Would need to join with supertokens_users
                    },
                }
                for member in members
            ]

        except Exception as e:
            logger.error(
                "Failed to get workspace members",
                workspace_id=workspace_id,
                error=str(e),
            )
            raise WorkspaceError("Failed to retrieve workspace members")

    async def _generate_unique_slug(self, base_slug: str) -> str:
        """Generate unique workspace slug"""
        slug = base_slug
        counter = 1

        while await self.uow.workspaces.slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def _get_owner_permissions(self) -> Dict[str, Any]:
        """Get owner permissions"""
        return {
            "billing": {"view": True, "edit": True},
            "mentions": {"assign": True, "respond": True, "delete": True},
            "monitors": {"edit": True, "create": True, "delete": True},
            "analytics": {"view": True, "export": True},
            "workspace": {"settings": True, "invite": True, "remove_members": True},
        }
