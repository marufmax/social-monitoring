"""
Async authentication service with proper transaction management
"""

from typing import Dict, Any, Optional
from fastapi import Request, Response
from supertokens_python.recipe.emailpassword.asyncio import sign_up, sign_in
from supertokens_python.recipe.session.asyncio import create_new_session
from app.core.unit_of_work import AbstractUnitOfWork
from app.schemas.auth import SignUpRequest, SignInRequest, UserResponse
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.utils import handle_supertokens_session
import structlog

logger = structlog.get_logger()


class AuthService:
    """Async authentication service"""

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def signup_with_email(
        self, signup_data: Dict[str, Any], request: Request, response: Response
    ) -> Dict[str, Any]:
        """Handle email/password signup with proper transaction management"""
        try:
            # Validate with Pydantic
            signup_request = SignUpRequest(**signup_data)

            # Create user in SuperTokens FIRST (external system)
            st_result = await sign_up(
                email=signup_request.email, password=signup_request.password
            )

            if st_result.status == "EMAIL_ALREADY_EXISTS_ERROR":
                raise AuthenticationError("Email already registered")
            elif st_result.status != "OK":
                raise AuthenticationError("Failed to create account")

            try:
                # Now create user profile in our database (within transaction)
                user_profile = await self.uow.users.create(
                    {
                        "user_id": st_result.user.user_id,
                        "name": signup_request.name,
                        "display_name": signup_request.display_name,
                        "timezone": signup_request.timezone,
                        "language": signup_request.language,
                        "consent_marketing": signup_request.consent_marketing,
                    }
                )

                # Create session and set cookies
                session = await create_new_session(
                    request=request, response=response, user_id=st_result.user.user_id
                )

                # If we get here, commit the transaction
                await self.uow.commit()

                logger.info(
                    "User signed up successfully",
                    user_id=st_result.user.user_id,
                    email=signup_request.email,
                )

                return {
                    "status": "OK",
                    "user": UserResponse.from_orm(user_profile),
                    "session_handle": session.get_handle(),
                }

            except Exception as db_error:
                # If database operations fail, we need to clean up SuperTokens user
                # In a production system, you might want to implement compensation
                logger.error(
                    "Database operation failed after SuperTokens signup",
                    user_id=st_result.user.user_id,
                    error=str(db_error),
                )
                raise AuthenticationError("Registration failed - please try again")

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Signup failed", error=str(e))
            raise AuthenticationError("Registration failed")

    async def signin_with_email(
        self, signin_data: Dict[str, Any], request: Request, response: Response
    ) -> Dict[str, Any]:
        """Handle email/password signin"""
        try:
            # Validate with Pydantic
            signin_request = SignInRequest(**signin_data)

            # Sign in with SuperTokens
            st_result = await sign_in(
                email=signin_request.email, password=signin_request.password
            )

            if st_result.status == "WRONG_CREDENTIALS_ERROR":
                raise AuthenticationError("Invalid email or password")
            elif st_result.status != "OK":
                raise AuthenticationError("Sign in failed")

            # Get user profile
            user_profile = await self.uow.users.get_by_id(
                st_result.user.user_id, load_workspaces=True
            )

            if not user_profile:
                # Edge case: SuperTokens user exists but no profile
                # Create minimal profile
                user_profile = await self.uow.users.create(
                    {
                        "user_id": st_result.user.user_id,
                        "name": signin_request.email.split("@")[0],
                        "timezone": "UTC",
                        "language": "en",
                        "consent_marketing": False,
                    }
                )
                await self.uow.commit()

            # Create session and set cookies
            session = await create_new_session(
                request=request, response=response, user_id=st_result.user.user_id
            )

            logger.info(
                "User signed in successfully",
                user_id=st_result.user.user_id,
                email=signin_request.email,
            )

            return {
                "status": "OK",
                "user": UserResponse.from_orm(user_profile),
                "session_handle": session.get_handle(),
            }

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Signin failed", error=str(e))
            raise AuthenticationError("Sign in failed")

    async def handle_social_auth_callback(
        self, supertokens_user_id: str, email: str, profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle social auth callback with race condition protection"""
        try:
            # Check if user profile already exists (race condition protection)
            existing_user = await self.uow.users.get_by_id(supertokens_user_id)

            if existing_user:
                return {
                    "status": "OK",
                    "user": UserResponse.from_orm(existing_user),
                    "is_new_user": False,
                }

            # Create new user profile with transaction protection
            try:
                user_profile = await self.uow.users.create(
                    {
                        "user_id": supertokens_user_id,
                        "name": profile_data.get("name", email.split("@")[0]),
                        "display_name": profile_data.get("display_name"),
                        "timezone": profile_data.get("timezone", "UTC"),
                        "language": profile_data.get("language", "en"),
                        "consent_marketing": profile_data.get(
                            "consent_marketing", False
                        ),
                    }
                )

                await self.uow.commit()

                logger.info(
                    "Social auth profile created",
                    user_id=supertokens_user_id,
                    email=email,
                )

                return {
                    "status": "OK",
                    "user": UserResponse.from_orm(user_profile),
                    "is_new_user": True,
                }

            except Exception as db_error:
                # Handle race condition - another request might have created the user
                await self.uow.rollback()

                # Try to get the user again
                existing_user = await self.uow.users.get_by_id(supertokens_user_id)
                if existing_user:
                    logger.info(
                        "User created by concurrent request",
                        user_id=supertokens_user_id,
                    )
                    return {
                        "status": "OK",
                        "user": UserResponse.from_orm(existing_user),
                        "is_new_user": False,
                    }

                # If still not found, re-raise the error
                raise db_error

        except Exception as e:
            logger.error(
                "Social auth callback failed", user_id=supertokens_user_id, error=str(e)
            )
            raise AuthenticationError("Failed to complete social authentication")

