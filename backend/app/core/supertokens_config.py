"""
Complete SuperTokens configuration with social login
"""

import os
from typing import List, Dict, Any
from supertokens_python import init, InputAppInfo, SupertokensConfig
from supertokens_python.recipe import emailpassword, session, thirdparty
from supertokens_python.recipe.thirdparty import (
    ProviderInput,
    ProviderConfig,
    ProviderClientConfig,
)
from supertokens_python.recipe.emailpassword.interfaces import (
    RecipeInterface as EmailPasswordInterface,
)
from supertokens_python.recipe.thirdparty.interfaces import (
    RecipeInterface as ThirdPartyInterface,
)
from app.core.config import settings
import structlog

logger = structlog.get_logger()


def override_emailpassword_functions(original_implementation: EmailPasswordInterface):
    """Override email/password functions"""
    original_sign_up = original_implementation.sign_up
    original_sign_in = original_implementation.sign_in

    async def sign_up(form_fields, user_context):
        email = next(field.value for field in form_fields if field.id == "email")
        logger.info("Email signup attempt", email=email)

        response = await original_sign_up(form_fields, user_context)

        if response.status == "OK":
            logger.info(
                "SuperTokens user created", user_id=response.user.user_id, email=email
            )

        return response

    async def sign_in(email: str, password: str, user_context):
        logger.info("Email signin attempt", email=email)

        response = await original_sign_in(email, password, user_context)

        if response.status == "OK":
            logger.info(
                "SuperTokens user signed in", user_id=response.user.user_id, email=email
            )

        return response

    original_implementation.sign_up = sign_up
    original_implementation.sign_in = sign_in

    return original_implementation


def override_thirdparty_functions(original_implementation: ThirdPartyInterface):
    """Override third party functions for social login"""
    original_sign_in_up = original_implementation.sign_in_up

    async def sign_in_up(
        third_party_id: str, third_party_user_id: str, email: str, user_context
    ):
        logger.info("Social auth attempt", provider=third_party_id, email=email)

        response = await original_sign_in_up(
            third_party_id, third_party_user_id, email, user_context
        )

        if response.status == "OK":
            logger.info(
                "Social auth successful",
                provider=third_party_id,
                user_id=response.user.user_id,
                is_new_user=response.created_new_user,
            )

        return response

    original_implementation.sign_in_up = sign_in_up
    return original_implementation


def init_supertokens():
    """Initialize SuperTokens with complete configuration"""

    app_info = InputAppInfo(
        app_name="Social Media Monitor",
        api_domain=settings.API_DOMAIN,
        website_domain=settings.FRONTEND_DOMAIN,
        api_base_path="/auth",
        website_base_path="/auth",
    )

    # Configure social login providers
    providers = []

    # Google OAuth
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        providers.append(
            ProviderInput(
                config=ProviderConfig(
                    third_party_id="google",
                    clients=[
                        ProviderClientConfig(
                            client_id=settings.GOOGLE_CLIENT_ID,
                            client_secret=settings.GOOGLE_CLIENT_SECRET,
                            scope=["openid", "email", "profile"],
                        )
                    ],
                )
            )
        )
        logger.info("Google OAuth provider configured")

    # GitHub OAuth
    if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
        providers.append(
            ProviderInput(
                config=ProviderConfig(
                    third_party_id="github",
                    clients=[
                        ProviderClientConfig(
                            client_id=settings.GITHUB_CLIENT_ID,
                            client_secret=settings.GITHUB_CLIENT_SECRET,
                            scope=["user:email"],
                        )
                    ],
                )
            )
        )
        logger.info("GitHub OAuth provider configured")

    # LinkedIn OAuth
    if settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET:
        providers.append(
            ProviderInput(
                config=ProviderConfig(
                    third_party_id="linkedin",
                    clients=[
                        ProviderClientConfig(
                            client_id=settings.LINKEDIN_CLIENT_ID,
                            client_secret=settings.LINKEDIN_CLIENT_SECRET,
                            scope=["r_liteprofile", "r_emailaddress"],
                        )
                    ],
                )
            )
        )
        logger.info("LinkedIn OAuth provider configured")

    recipe_list = [
        emailpassword.init(
            override=emailpassword.InputOverrideConfig(
                functions=override_emailpassword_functions
            )
        ),
        session.init(
            anti_csrf="VIA_TOKEN"
            if settings.ENVIRONMENT == "production"
            else "VIA_CUSTOM_HEADER",
            cookie_domain=settings.COOKIE_DOMAIN,
            cookie_secure=settings.ENVIRONMENT == "production",
            cookie_same_site="none" if settings.ENVIRONMENT == "production" else "lax",
            session_expired_status_code=401,
            override=session.InputOverrideConfig(
                error_handlers=session.ErrorHandlers(
                    on_unauthorised=lambda _req, _err, response: response
                )
            ),
        ),
    ]

    # Add third party recipe if providers are configured
    if providers:
        recipe_list.append(
            thirdparty.init(
                providers=providers,
                override=thirdparty.InputOverrideConfig(
                    functions=override_thirdparty_functions
                ),
            )
        )

    init(
        app_info=app_info,
        supertokens_config=SupertokensConfig(
            connection_uri=settings.SUPERTOKENS_CONNECTION_URI,
            api_key=settings.SUPERTOKENS_API_KEY,
        ),
        framework="fastapi",
        recipe_list=recipe_list,
        mode="asgi",
    )

    logger.info("SuperTokens initialized successfully")
