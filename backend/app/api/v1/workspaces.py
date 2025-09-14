"""
Async workspace management endpoints
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from app.core.auth_dependencies import CurrentUserDep
from app.core.unit_of_work import AbstractUnitOfWork, get_unit_of_work
from app.models.workspace import WorkspaceRole
from app.schemas.workspace import (
    WorkspaceResponse,
)
from app.services.workspace_service import WorkspaceService
from app.core.exceptions import WorkspaceError, AuthorizationError
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


class CreateWorkspaceRequest(BaseModel):
    """Create workspace request"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.get("/", response_model=List[WorkspaceResponse])
async def list_user_workspaces(
    current_user: CurrentUserDep,
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
):
    """List all workspaces for current user"""
    try:
        async with uow:
            workspace_service = WorkspaceService(uow)
            workspaces = await workspace_service.get_user_workspaces(
                current_user.user_id
            )

            return [
                WorkspaceResponse(
                    **workspace,
                    user_role=current_user.get_workspace_role(workspace["id"]),
                )
                for workspace in workspaces
            ]

    except Exception as e:
        logger.error(
            "Failed to list workspaces", user_id=current_user.user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workspaces",
        )


@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    workspace_data: CreateWorkspaceRequest,
    current_user: CurrentUserDep,
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
):
    """Create a new workspace"""
    try:
        async with uow:
            workspace_service = WorkspaceService(uow)
            workspace = await workspace_service.create_workspace(
                workspace_data.dict(), created_by=current_user.user_id
            )

            return WorkspaceResponse(**workspace, user_role=WorkspaceRole.OWNER.value)

    except Exception as e:
        logger.error(
            "Failed to create workspace", user_id=current_user.user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workspace",
        )


@router.get("/{workspace_id}/members")
async def list_workspace_members(
    current_user: CurrentUserDep,
    workspace_id: str = Path(..., description="Workspace ID"),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List workspace members (requires member access)"""
    try:
        async with uow:
            workspace_service = WorkspaceService(uow)

            # Check if user has access to this workspace
            has_access = await workspace_service.check_user_access(
                current_user.user_id, workspace_id
            )

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            members = await workspace_service.get_workspace_members(
                workspace_id, skip=skip, limit=limit
            )

            return {
                "status": "OK",
                "members": members,
                "total": len(members),
                "workspace_id": workspace_id,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list members", workspace_id=workspace_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workspace members",
        )
