from fastapi import APIRouter, HTTPException, status, Depends
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer
from app.schemas.auth import (
    UserResponse,
    UpdateProfileRequest,
)
from app.core.auth_dependencies import CurrentUserDep
from app.core.unit_of_work import AbstractUnitOfWork, get_unit_of_work
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: CurrentUserDep):
    """Get current user profile with workspaces"""
    try:
        return UserResponse.from_user_with_workspaces(
            user=current_user, workspace_memberships=current_user.workspace_memberships
        )

    except Exception as e:
        logger.error(
            "Failed to get profile", user_id=current_user.user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile",
        )


@router.put("/me", response_model=UserResponse)
async def update_profile(
    update_data: UpdateProfileRequest,
    current_user: CurrentUserDep,
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
):
    """Update current user profile"""
    try:
        async with uow:
            # Filter out None values
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

            if not update_dict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid fields to update",
                )

            updated_user = await uow.users.update(current_user.user_id, update_dict)

            if not updated_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            return UserResponse.from_user_with_workspaces(
                user=updated_user,
                workspace_memberships=updated_user.workspace_memberships,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Profile update failed", user_id=current_user.user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed",
        )


@router.get("/session")
async def get_session_info(session: SessionContainer = Depends(verify_session())):
    """Get current session information"""
    try:
        user_id = session.get_user_id()
        handle = session.get_handle()

        return {
            "user_id": user_id,
            "session_handle": handle,
            "expires_at": None,  # SuperTokens handles this internally
        }
    except Exception as e:
        logger.error("Failed to get session info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session information",
        )
