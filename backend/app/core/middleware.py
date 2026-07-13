import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

# Routes to skip audit logging (health checks, metrics)
_SKIP_AUDIT = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' wss:;"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        path = request.url.path

        log_data = dict(
            trace_id=trace_id,
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            ip=request.client.host if request.client else "unknown",
        )

        if response.status_code >= 500:
            logger.error("http_request", **log_data)
        elif response.status_code >= 400:
            logger.warning("http_request", **log_data)
        elif path not in _SKIP_AUDIT:
            logger.info("http_request", **log_data)

        response.headers["X-Trace-ID"] = trace_id

        # Async write to audit_logs table for non-health paths
        if path not in _SKIP_AUDIT and request.method in ("POST", "PUT", "DELETE", "PATCH"):
            _write_audit_log_bg(request, response.status_code, trace_id)

        return response


def _write_audit_log_bg(request: Request, status_code: int, trace_id: str) -> None:
    """Fire-and-forget audit log write — failures are silently ignored."""
    import asyncio

    from app.core.database import AsyncSessionLocal
    from app.core.security import decode_token
    from app.models.audit_log import AuditLog

    user_id = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_token(auth.split(" ", 1)[1])
        if payload:
            try:
                from uuid import UUID
                user_id = UUID(payload["sub"])
            except Exception:
                pass

    async def _write():
        try:
            async with AsyncSessionLocal() as db:
                db.add(AuditLog(
                    user_id=user_id,
                    action=f"{request.method} {request.url.path}",
                    metadata_={"status_code": status_code, "trace_id": trace_id},
                    ip_addr=request.client.host if request.client else None,
                ))
                await db.commit()
        except Exception as e:
            logger.debug("audit_log_write_failed", error=str(e))

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.ensure_future(_write())
            # Shield the task so test teardown doesn't raise "Task destroyed" warnings
            task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    except Exception:
        pass
