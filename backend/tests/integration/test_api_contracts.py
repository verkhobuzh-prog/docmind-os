"""
API Contract тести — перевіряємо структуру відповідей endpoints.
Без реальних даних — тільки схеми та HTTP коди.
"""

import pytest
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient


@asynccontextmanager
async def api_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestAPIContracts:
    """HTTP коди і структури відповідей."""

    @pytest.mark.asyncio
    async def test_health_returns_200_with_status(self):
        from app.main import app

        async with api_client(app) as c:
            r = await c.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_docs_returns_200_in_dev(self):
        from app.main import app

        async with api_client(app) as c:
            r = await c.get("/docs")
        # В dev режимі Swagger доступний
        assert r.status_code in (200, 404)  # 404 якщо production mode

    @pytest.mark.asyncio
    async def test_documents_401_without_token(self):
        from app.main import app

        async with api_client(app) as c:
            r = await c.get("/api/v1/documents")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_401_without_token(self):
        from app.main import app

        async with api_client(app) as c:
            r = await c.post("/api/v1/chat", json={"query": "test"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_profiles_401_without_token(self):
        from app.main import app

        async with api_client(app) as c:
            r = await c.get("/api/v1/profiles")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_invites_401_without_token(self):
        from app.main import app

        async with api_client(app) as c:
            r = await c.get("/api/v1/invites")
        assert r.status_code in (401, 404)  # 404 якщо ще не підключено

    def test_all_v1_routes_registered(self):
        """Перевіряємо що всі очікувані routes є."""
        from app.main import app

        paths = [r.path for r in app.routes]
        v1 = [p for p in paths if "/api/v1/" in p]
        expected_prefixes = [
            "/api/v1/documents",
            "/api/v1/chat",
            "/api/v1/profiles",
        ]
        for prefix in expected_prefixes:
            matches = [p for p in v1 if p.startswith(prefix)]
            assert matches, (
                f"Route prefix '{prefix}' не зареєстровано. V1 routes: {v1}"
            )
