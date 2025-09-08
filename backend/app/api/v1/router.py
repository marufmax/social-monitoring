from fastapi import APIRouter

from app.api.v1.health import health_router

api_router = APIRouter()


## Routes
api_router.include_router(health_router)