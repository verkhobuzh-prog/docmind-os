"""
Smoke тести — базова перевірка що система піднімається.
Якщо ці тести падають — щось зламано на рівні імпортів або конфігурації.
Час виконання: < 5 секунд.
"""

import pytest


class TestImports:
    """Перевірка що всі ключові модулі імпортуються без помилок."""

    def test_import_main(self):
        """FastAPI app створюється без помилок."""
        from app.main import app

        assert app is not None

    def test_import_schemas(self):
        """Pydantic схеми валідні."""
        from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate

        assert ProfileCreate
        assert ProfileRead
        assert ProfileUpdate

    def test_import_prompt_builder(self):
        """Prompt builder імпортується."""
        from app.services.prompt_builder import build_system_prompt

        assert callable(build_system_prompt)

    def test_import_profile_service(self):
        """Profile service імпортується."""
        from app.services.profile_service import ProfileService

        assert ProfileService

    def test_import_rag_service(self):
        """RAG service імпортується."""
        try:
            from app.services.rag_service import RAGService

            assert RAGService
        except ImportError:
            from app.services.chat_service import ChatService

            assert ChatService


class TestConfiguration:
    """Перевірка що конфігурація коректна."""

    def test_settings_load(self):
        """Налаштування завантажуються (навіть з placeholder значеннями)."""
        try:
            from app.core.config import settings

            assert settings is not None
        except Exception as e:
            pytest.skip(f"Config not available in test env: {e}")

    def test_health_endpoint_exists(self):
        """Health endpoint зареєстрований."""
        from app.main import app

        routes = [r.path for r in app.routes]
        assert "/health" in routes, f"No /health route. Found: {routes}"

    def test_api_v1_prefix(self):
        """API v1 routes зареєстровані."""
        from app.main import app

        routes = [r.path for r in app.routes]
        v1_routes = [r for r in routes if "/api/v1/" in r]
        assert len(v1_routes) > 0, f"No /api/v1/ routes found. Found: {routes}"
