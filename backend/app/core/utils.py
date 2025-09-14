"""
Utility functions for the application
"""

"""
Utility functions for the application
"""
from typing import Dict, Any, Optional
from fastapi import Request, Response
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.asyncio import create_new_session
import structlog

logger = structlog.get_logger()


async def handle_supertokens_session(
    request: Request, response: Response, user_id: str
) -> SessionContainer:
    """Create SuperTokens session and handle cookies"""
    try:
        session = await create_new_session(
            request=request, response=response, user_id=user_id
        )

        logger.debug("SuperTokens session created", user_id=user_id)
        return session

    except Exception as e:
        logger.error("Failed to create session", user_id=user_id, error=str(e))
        raise


def slugify(text: str) -> str:
    """Simple slugify function"""
    import re

    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip('-')
