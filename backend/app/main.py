from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.middleware import LoggingMiddleware
from app.api.v1.router import api_router
from app.database import Base, engine, AsyncSessionLocal
from sqlalchemy import text
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    # Create tables if not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Optionally check DB connection
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))

    yield  # The application runs here

    # Shutdown code
    await engine.dispose()


app = FastAPI(
    title="Social Media Monitoring",
    lifespan=lifespan
)

# Middleware
app.add_middleware(LoggingMiddleware)

# Routes
app.include_router(api_router, prefix="/api/v1")


# Health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "Social Media Monitoring API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "to implement",
        "redis": "to implement",
        "opensearch": "to implement",
        "collectors": "to implement",
    }
