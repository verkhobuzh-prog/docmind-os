"""
Redis-based Rate Limiting Middleware для DocMind OS.

═══════════════════════════════════════════════════════════════════════
ВЕКТОР АТАКИ: RATE_LIMIT_PER_MINUTE оголошено в config, але не підключено
═══════════════════════════════════════════════════════════════════════

ДО (проблема):
──────────────
  settings.RATE_LIMIT_PER_MINUTE = 60  # є в config.py
  # Але ніде не використовується!
  # → Будь-який IP може:
  #   1. Спамити POST /chat → дорогі OpenAI виклики ($$$)
  #   2. Brute-force JWT токени через POST /auth/*
  #   3. Flood ingestion pipeline → OOM на parse_document
  #   4. DoS через POST /documents/upload (disk + Supabase Storage)

ПІСЛЯ (цей файл):
─────────────────
  Sliding window counter у Redis.
  Різні ліміти для різних endpoint груп (chat дорожчий → менший ліміт).
  Graceful fallback: якщо Redis недоступний → allow (не блокуємо prod).
  Стандартні заголовки: X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After.

Підключення (1 рядок у main.py):
──────────────────────────────────
  from app.middleware.rate_limit import RateLimitMiddleware
  app.add_middleware(RateLimitMiddleware)

═══════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger("docmind.rate_limit")

# ─── Конфігурація лімітів по prefix ───────────────────────────────────────────
# Формат: (url_prefix, requests_per_minute, window_seconds)
# Порядок важливий: перший match перемагає.
# Більш специфічні prefix — вище в списку.
_ROUTE_LIMITS: list[tuple[str, int, int]] = [
    # Chat — дорогий (OpenAI), менший ліміт
    ("/api/v1/chat", 20, 60),
    # Ingestion — важкий (CPU + Storage), окремий ліміт
    ("/api/v1/documents", 30, 60),
    # Auth — захист від brute force
    ("/api/v1/auth", 20, 60),
    # Knowledge / reasoning — LLM calls
    ("/api/v1/knowledge", 30, 60),
    ("/api/v1/reasoning", 15, 60),
    # Default — всі інші endpoints
    ("/api/v1", settings.RATE_LIMIT_PER_MINUTE, 60),
    # Health check — не обмежуємо (load balancer probe)
    ("/health", 10000, 60),
]

# Endpoints що повністю виключені з rate limiting
_EXCLUDED_PATHS: frozenset[str] = frozenset({
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
})


def _get_limit_for_path(path: str) -> tuple[int, int]:
    """
    Повертає (requests_per_window, window_seconds) для шляху.
    Перший match по prefix перемагає.
    """
    for prefix, limit, window in _ROUTE_LIMITS:
        if path.startswith(prefix):
            return limit, window
    return settings.RATE_LIMIT_PER_MINUTE, 60


def _get_client_key(request: Request) -> str:
    """
    Унікальний ключ клієнта для rate limiting.

    Пріоритет:
      1. Authenticated user_id (з state — встановлюється security middleware)
      2. X-Forwarded-For (за проксі/load balancer)
      3. client.host (прямий IP)

    Важливо: IP-based ліміти легко обійти через проксі, але це перший рівень.
    User-based ліміти (user_id) стійкіші — підключаються автоматично після auth.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"rl:user:{user_id}"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        return f"rl:ip:{client_ip}"

    client_host = request.client.host if request.client else "unknown"
    return f"rl:ip:{client_host}"


async def _check_rate_limit(
    redis_client,
    key: str,
    limit: int,
    window: int,
) -> tuple[bool, int, int]:
    """
    Sliding window rate limit через Redis.

    Алгоритм: Sorted Set з timestamp як score.
      1. Видаляємо застарілі записи (старші за window)
      2. Рахуємо поточну кількість запитів
      3. Якщо < limit: додаємо поточний timestamp → allow
      4. Якщо >= limit: reject, повертаємо час до наступного вікна

    Returns:
        (allowed: bool, current_count: int, retry_after_seconds: int)

    Чому sorted set а не simple counter:
      - Simple INCR + TTL: при лімітуванні точно в момент reset вікна
        можна зробити 2*limit запитів (double-spend attack на вікно).
      - Sliding window: кожен запит "пам'ятає" свій timestamp → точний ліміт.
    """
    now = time.time()
    window_start = now - window
    full_key = f"{key}:{window}"

    try:
        pipeline = redis_client.pipeline()
        pipeline.zremrangebyscore(full_key, 0, window_start)
        pipeline.zcard(full_key)
        pipeline.zadd(full_key, {f"{now:.6f}": now})
        pipeline.expire(full_key, window * 2)
        results = await pipeline.execute()

        current_count = results[1]

        if current_count >= limit:
            oldest_entries = await redis_client.zrange(full_key, 0, 0, withscores=True)
            if oldest_entries:
                oldest_ts = oldest_entries[0][1]
                retry_after = max(1, int(oldest_ts + window - now) + 1)
            else:
                retry_after = window

            await redis_client.zremrangebyscore(full_key, now - 0.001, now + 0.001)
            return False, current_count, retry_after

        return True, current_count + 1, 0

    except Exception as exc:
        logger.warning(
            "Rate limit Redis error (fail open): %s",
            exc,
            extra={"key": key},
        )
        return True, 0, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiting middleware.

    Підключення в main.py:
        from app.middleware.rate_limit import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)

    ВАЖЛИВО: add_middleware() додає в стек LIFO.
    RateLimitMiddleware треба додавати ПІСЛЯ RequestContextMiddleware щоб
    X-Request-ID вже був встановлений до логування rate limit events.

    Правильний порядок у main.py:
        app.add_middleware(RequestContextMiddleware)   # додається першим
        app.add_middleware(RateLimitMiddleware)         # перевіряється першим
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if path in _EXCLUDED_PATHS:
            return await call_next(request)

        redis_client = _get_redis_client()
        if redis_client is None:
            return await call_next(request)

        limit, window = _get_limit_for_path(path)
        client_key = _get_client_key(request)

        allowed, current, retry_after = await _check_rate_limit(
            redis_client, client_key, limit, window
        )

        if not allowed:
            logger.warning(
                "Rate limit exceeded: key=%s path=%s limit=%d/%ds",
                client_key,
                path,
                limit,
                window,
                extra={
                    "request_id": getattr(request.state, "request_id", "-"),
                    "client_key": client_key,
                    "path": path,
                    "limit": limit,
                    "window": window,
                },
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit exceeded: {limit} requests per {window}s",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                },
            )

        response = await call_next(request)
        remaining = max(0, limit - current)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)
        return response


def _get_redis_client():
    """
    Lazy-get Redis клієнт.
    Повертає None якщо Redis не налаштований або недоступний.
    """
    try:
        from app.db.redis import get_redis

        return get_redis()
    except Exception:
        return None
