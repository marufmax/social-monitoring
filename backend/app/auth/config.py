import structlog
from supertokens_python import init
from supertokens_python.recipe import session, emailpassword
from supertokens_python.framework.fastapi import get_middleware
from fastapi import FastAPI

from app.config import settings
logger = structlog.getLogger()

def validate_email(email: str) -> str:
    """Email validation"""
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise ValueError("Invalid email format")
    return email


def init_supertokens(app: FastAPI):
    """
    Initialize SuperTokens for FastAPI
    """
    init(
        app_info={
            "app_name": "Social Media Monitor",
            "api_domain": "http://localhost:8000",
            "website_domain": "http://localhost:3000",
        },
        framework="fastapi",
        supertokens_config={
            "connection_uri": settings.SUPERTOKENS_CONNECTION_URI,
        },
        recipe_list=[
            emailpassword.init(),
            session.init()
        ],
    )

    # Add middleware to FastAPI
    app.add_middleware(get_middleware())
