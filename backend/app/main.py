from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.db import close_redis, close_supabase, init_redis, init_supabase, ping_redis, ping_supabase
from app.db.postgres import close_postgres, init_postgres
from app.middleware.request_context import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_supabase()
    await init_redis()
    await init_postgres()
    yield
    await close_redis()
    await close_postgres()
    close_supabase()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="DocMind OS — Enterprise AI Document SaaS API",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    register_exception_handlers(app)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.get("/health", tags=["health"])
    async def health_check():
        supabase_ok = await ping_supabase()
        redis_ok = await ping_redis()
        health_status = "ok" if (supabase_ok or not settings.supabase_configured) else "degraded"
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
