import asyncio
from fastapi import APIRouter
import redis.asyncio as pyredis
import asyncpg
from opensearchpy import AsyncOpenSearch

from app.config import Settings
from app.database import ASYNC_DATABASE_URL

health_router = APIRouter()
# --- Health check helpers ---

async def check_database():
    try:
        conn = await asyncpg.connect(ASYNC_DATABASE_URL)
        await conn.execute("SELECT 1;")
        await conn.close()
        return "ok"
    except Exception as e:
        return f"down ({str(e)})"


async def check_redis():
    try:
        redis_client = await pyredis.Redis.from_url(Settings.REDIS_URL)
        pong = await redis_client.ping()
        await redis_client.close()
        return "ok" if pong else "down"
    except Exception as e:
        return f"down ({str(e)})"


async def check_opensearch() -> str:
    try:
        client = AsyncOpenSearch(
            hosts=["http://localhost:9200"],
            http_compress=True,
        )
        health = await client.cluster.health()
        await client.close()
        return "ok" if health.get("status") in ["green", "yellow"] else "down"
    except Exception as e:
        return f"down ({str(e)})"


async def check_collectors():
    # Example: simulate calling external collectors
    try:
        # Replace with actual check logic (HTTP call, RPC, etc.)
        await asyncio.sleep(0.1)
        return "ok"
    except Exception as e:
        return f"down ({str(e)})"


# --- API route ---

@health_router.get("/health")
async def health_check():
    db, redis, opensearch, collectors = await asyncio.gather(
        check_database(), check_redis(), check_opensearch(), check_collectors()
    )
    return {
        "status": "healthy" if all(v == "ok" for v in [db, redis, opensearch, collectors]) else "degraded",
        "database": db,
        "redis": redis,
        "opensearch": opensearch,
        "collectors": collectors,
    }
