from fastapi import APIRouter
from app.api.v1 import auth, users, workspaces
apiV1_router = APIRouter()
apiV1_router.include_router(auth.router, prefix="/auth")
apiV1_router.include_router(users.router, prefix="/users")
apiV1_router.include_router(workspaces.router, prefix="/workspaces")
