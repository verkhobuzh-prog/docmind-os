"""
DocMind OS — main.py після security audit fixes.

Зміни відносно оригіналу:
  1. run_startup_security_checks() — перша дія в lifespan
  2. RateLimitMiddleware — підключено
  3. Порядок middleware задокументований
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.telemetry import init_telemetry
from app.core.startup_validation import (
    StartupSecurityError,
    run_startup_security_checks,
)
from app.db import close_redis, close_supabase, init_redis, init_supabase, ping_redis, ping_supabase
from app.db.postgres import close_postgres, init_postgres
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware

logger = get_logger("docmind.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # ════════════════════════════════════════════════════
    # КРОК 1: Security validation — ПЕРШ НІЖ що-небудь інше
    # ════════════════════════════════════════════════════
    try:
        run_startup_security_checks(settings)
    except StartupSecurityError as exc:
        logger.critical("Startup aborted due to security violation: %s", exc)
        raise

    # ════════════════════════════════════════════════════
    # КРОК 2: Звичайна ініціалізація
    # ════════════════════════════════════════════════════
    logger.info(
        "Starting DocMind OS backend (env=%s, auth_disabled=%s)",
        settings.ENVIRONMENT,
        settings.auth_disabled,
    )
    init_supabase()
    await init_redis()
    await init_postgres()
    logger.info("DocMind OS backend started successfully.")

    yield

    # ════════════════════════════════════════════════════
    # КРОК 3: Graceful shutdown
    # ════════════════════════════════════════════════════
    logger.info("Shutting down DocMind OS backend...")
    await close_redis()
    await close_postgres()
    close_supabase()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="DocMind OS — Enterprise AI Document SaaS API",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    init_telemetry(app)

    register_exception_handlers(app)

    # ════════════════════════════════════════════════════
    # Middleware — порядок ВАЖЛИВИЙ (LIFO execution):
    #
    #   add_middleware() порядок    →    виконання (request)
    #   ─────────────────────────────────────────────────
    #   1. RequestContextMiddleware →  3. виконується 3-м  (inner)
    #   2. RateLimitMiddleware      →  2. виконується 2-м
    #   3. CORSMiddleware           →  1. виконується 1-м  (outer)
    #
    # Запит проходить: CORS → RateLimit → RequestContext → handler
    # Відповідь йде зворотньо: handler → RequestContext → RateLimit → CORS
    #
    # Чому саме такий порядок:
    #   - CORS першим: preflight OPTIONS не витрачає rate limit quota
    #   - RateLimit другим: блокуємо до бізнес-логіки, X-Request-ID вже є
    #   - RequestContext: встановлює request_id для логів
    # ════════════════════════════════════════════════════

    app.add_middleware(RequestContextMiddleware)  # ← додається 1-м → виконується внутрішнім

    # ▼ НОВИЙ (Крок 5) ▼
    app.add_middleware(RateLimitMiddleware)  # ← додається 2-м → виконується середнім

    origins = list(settings.cors_origins_list)
    if settings.FRONTEND_URL and settings.FRONTEND_URL not in origins:
        origins.append(settings.FRONTEND_URL.rstrip("/"))

    app.add_middleware(  # ← зовнішній (виконується першим)
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    # ════════════════════════════════════════════════════
    # Health endpoint (без змін)
    # ════════════════════════════════════════════════════
    @app.get("/health", tags=["health"])
    async def health_check():
        supabase_ok = await ping_supabase()
        redis_ok = await ping_redis()
        health_status = (
            "ok"
            if (supabase_ok or not settings.supabase_configured)
            else "degraded"
        )
        return {
            "status": health_status,
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "checks": {
                "supabase": supabase_ok if settings.supabase_configured else "not_configured",
                "redis": redis_ok if settings.redis_configured else "not_configured",
            },
        }

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
