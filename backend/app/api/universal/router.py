from fastapi import APIRouter

from app.api.universal.health import health_router

api_universal_router = APIRouter()

api_universal_router.include_router(health_router)