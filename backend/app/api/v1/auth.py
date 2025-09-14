"""
Async authentication endpoints with proper session and transaction handling
"""

from typing import Dict, Any
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.asyncio import revoke_session
from app.schemas.auth import (
    SignUpRequest,
    SignInRequest,
    UserResponse,
    UpdateProfileRequest,
)
from app.services.auth_service import AuthService
from app.core.auth_dependencies import CurrentUserDep
from app.core.unit_of_work import AbstractUnitOfWork, get_unit_of_work
from app.core.exceptions import AuthenticationError, ValidationError
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=Dict[str, Any])
async def signup(
    request: Request,
    response: Response,
    signup_data: SignUpRequest,
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
):
    """Register new user with email and password"""
    try:
        async with uow:
            auth_service = AuthService(uow)
            result = await auth_service.signup_with_email(
                signup_data.dict(), request, response
            )

            return {
                "status": "OK",
                "message": "Account created successfully",
                "user": result["user"].dict(),
                "session_handle": result["session_handle"],
            }

    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "field": getattr(e, "field", None)},
        )
    except Exception as e:
        logger.error("Signup failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/signin", response_model=Dict[str, Any])
async def signin(
    request: Request,
    response: Response,
    signin_data: SignInRequest,
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
):
    """Sign in with email and password"""
    try:
        async with uow:
            auth_service = AuthService(uow)
            result = await auth_service.signin_with_email(
                signin_data.dict(), request, response
            )

            return {
                "status": "OK",
                "message": "Signed in successfully",
                "user": result["user"].dict(),
                "session_handle": result["session_handle"],
            }

    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error("Signin failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sign in failed"
        )


@router.post("/signout")
async def signout(session: SessionContainer = Depends(verify_session())):
    """Sign out current user"""
    try:
        await revoke_session(session.get_handle())
        logger.info("User signed out", user_id=session.get_user_id())
        return {"status": "OK", "message": "Signed out successfully"}
    except Exception as e:
        logger.error("Signout failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sign out failed"
        )

