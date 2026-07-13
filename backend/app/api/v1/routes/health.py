from fastapi import APIRouter

from app.core.database import engine
from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health():
    checks = {"status": "ok", "database": "ok", "redis": "ok"}
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception as e:
        checks["database"] = f"error: {e}"
        checks["status"] = "degraded"

    try:
        redis = await get_redis()
        await redis.ping()
    except Exception as e:
        checks["redis"] = f"error: {e}"
        checks["status"] = "degraded"

    return checks
