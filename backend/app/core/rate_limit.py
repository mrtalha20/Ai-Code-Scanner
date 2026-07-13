from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings


def _get_rate_limit_key(request: Request) -> str:
    """Use user ID from JWT if authenticated, else IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        from app.core.security import decode_token
        payload = decode_token(token)
        if payload:
            plan = payload.get("plan", "free")
            return f"user:{payload['sub']}:{plan}"
    return f"ip:{get_remote_address(request)}"


def _get_limit_for_key(key: str) -> str:
    if ":pro:" in key:
        return f"{settings.RATE_LIMIT_PRO_RPM}/minute"
    return f"{settings.RATE_LIMIT_FREE_RPM}/minute"


limiter = Limiter(key_func=_get_rate_limit_key)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Upgrade to Pro for higher limits.",
            "retry_after": str(exc.retry_after) if hasattr(exc, "retry_after") else "60",
        },
        headers={"Retry-After": "60"},
    )
