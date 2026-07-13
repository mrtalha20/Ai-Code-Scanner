from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded

from app.api.v1.routes import auth, github, health, scans
from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging
from app.core.middleware import AuditLogMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.core.redis import close_redis

configure_logging()
logger = structlog.get_logger()


def _validate_secrets():
    errors = []
    if not settings.JWT_SECRET or len(settings.JWT_SECRET) < 16:
        errors.append("JWT_SECRET is too short or missing")
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "gsk_...your_groq_api_key_here":
        errors.append("GROQ_API_KEY is not set")
    if errors:
        for e in errors:
            logger.error("startup_validation_failed", error=e)
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(f"Startup blocked — {'; '.join(errors)}")
        logger.warning("running_with_missing_secrets_in_dev_mode")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_secrets()
    logger.info("startup", environment=settings.ENVIRONMENT)
    yield
    await engine.dispose()
    await close_redis()
    logger.info("shutdown")


app = FastAPI(
    title="AI Code Security Scanner",
    description="OWASP Top 10 vulnerability detection with AI-powered fix suggestions",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# ── Rate limiter ──────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# ── Custom middleware ──────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditLogMiddleware)

# ── Prometheus metrics ────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ── Routers ───────────────────────────────────────────────────
app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["auth"])
app.include_router(scans.router, prefix=settings.API_V1_PREFIX, tags=["scans"])
app.include_router(github.router, prefix=settings.API_V1_PREFIX, tags=["github"])
