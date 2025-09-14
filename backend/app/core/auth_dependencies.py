"""
Async authentication dependencies
"""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer
from app.models.user import AppUser
from app.core.unit_of_work import AbstractUnitOfWork, get_unit_of_work
import structlog

logger = structlog.get_logger()


async def get_current_user(
    session: SessionContainer = Depends(verify_session()),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
) -> AppUser:
    """Get current authenticated user with proper async session handling"""
    try:
        async with uow:
            supertokens_user_id = session.get_user_id()
            user = await uow.users.get_by_id(supertokens_user_id, load_workspaces=True)

            if not user:
                logger.error(
                    "User profile not found", supertokens_user_id=supertokens_user_id
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User profile not found",
                )

            return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get current user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error",
        )


async def get_optional_user(
    session: Optional[SessionContainer] = Depends(
        verify_session(session_required=False)
    ),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
) -> Optional[AppUser]:
    """Get current user if authenticated, None otherwise"""
    if not session:
        return None

    try:
        async with uow:
            supertokens_user_id = session.get_user_id()
            return await uow.users.get_by_id(supertokens_user_id)
    except Exception:
        return None

CurrentUserDep = Annotated[AppUser, Depends(get_current_user)]
OptionalUserDep = Annotated[Optional[AppUser], Depends(get_optional_user)]