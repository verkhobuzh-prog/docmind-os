"""
Shared fixtures для всіх тестів DocMind OS.
Принцип: мокаємо зовнішні сервіси (Supabase, OpenAI),
тестуємо власну логіку.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.security import DEV_USER_ID, get_current_user
from app.main import app
from app.schemas.chat import ChatResponse, Citation, Source
from app.schemas.document import DocumentListResponse, DocumentResponse, DocumentUploadResponse
from app.schemas.ingestion import IngestionResponse, IngestionStatus
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.rag_service import RAGService

TEST_USER = {
    "id": DEV_USER_ID,
    "email": "test@example.com",
    "role": "authenticated",
    "org_id": None,
    "app_metadata": {},
    "user_metadata": {},
}


# ---------- Test user ----------
@pytest.fixture
def test_user_id() -> str:
    return "test-user-00000000-0000-0000-0000-000000000001"


# ---------- Test profiles ----------
@pytest.fixture
def education_profile_l1():
    """Школяр 5-6 клас — найпростіший рівень."""
    from app.schemas.profile import ProfilePreferences, ProfileRead

    return ProfileRead(
        id=uuid4(),
        user_id=uuid4(),
        name="5 клас Алгебра",
        complexity_level=1,
        domain="education",
        is_active=True,
        preferences=ProfilePreferences(
            response_style="concise",
            language="uk",
            forbidden_topics=[],
            temperature=0.2,
        ),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def education_profile_l5():
    """Студент / олімпіадник — експертний рівень."""
    from app.schemas.profile import ProfilePreferences, ProfileRead

    return ProfileRead(
        id=uuid4(),
        user_id=uuid4(),
        name="Олімпіада з математики",
        complexity_level=5,
        domain="education",
        is_active=True,
        preferences=ProfilePreferences(response_style="detailed", language="uk"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def legal_profile_l5():
    """Юрист — експертний рівень."""
    from app.schemas.profile import ProfilePreferences, ProfileRead

    return ProfileRead(
        id=uuid4(),
        user_id=uuid4(),
        name="Юридичний режим",
        complexity_level=5,
        domain="legal",
        is_active=True,
        preferences=ProfilePreferences(response_style="detailed", language="uk"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def business_profile_l3():
    """Менеджер — середній рівень."""
    from app.schemas.profile import ProfilePreferences, ProfileRead

    return ProfileRead(
        id=uuid4(),
        user_id=uuid4(),
        name="Бізнес-аналітик",
        complexity_level=3,
        domain="business",
        is_active=True,
        preferences=ProfilePreferences(response_style="balanced", language="uk"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# ---------- Mock Supabase ----------
@pytest.fixture
def mock_supabase():
    """Повний мок Supabase клієнта."""
    mock = MagicMock()
    table_mock = MagicMock()
    execute_mock = AsyncMock(return_value=MagicMock(data=[], error=None))

    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.single.return_value = table_mock
    table_mock.maybe_single.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.execute = execute_mock

    mock.table.return_value = table_mock
    return mock


# ---------- Mock OpenAI ----------
@pytest.fixture
def mock_openai_chat():
    """Мок OpenAI chat completion."""
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="Тестова відповідь AI."))]
    return AsyncMock(return_value=response)


@pytest.fixture
def mock_embeddings():
    """Мок embeddings — повертає вектор з 1536 вимірів."""
    import random

    vec = [random.uniform(-1, 1) for _ in range(1536)]
    response = MagicMock()
    response.data = [MagicMock(embedding=vec)]
    return AsyncMock(return_value=response)


# ---------- Sample documents ----------
@pytest.fixture
def sample_chunks():
    """Тестові фрагменти документів для RAG."""
    return [
        {
            "chunk_id": "chunk-001",
            "content": "Орендар зобов'язаний сплачувати орендну плату в розмірі 5000 грн щомісяця до 10 числа.",
            "similarity": 0.95,
            "document_id": "doc-001",
            "metadata": {"filename": "contract.pdf", "page": 1},
        },
        {
            "chunk_id": "chunk-002",
            "content": "Договір укладається терміном на 12 місяців з дати підписання.",
            "similarity": 0.88,
            "document_id": "doc-001",
            "metadata": {"filename": "contract.pdf", "page": 1},
        },
        {
            "chunk_id": "chunk-003",
            "content": "У разі затримки оплати більш ніж на 5 днів нараховується пеня 0.1% від суми боргу.",
            "similarity": 0.82,
            "document_id": "doc-001",
            "metadata": {"filename": "contract.pdf", "page": 2},
        },
    ]


# ---------- Legacy API test fixtures ----------
@pytest.fixture(autouse=True)
def pilot_settings(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.PILOT_INVITE_REQUIRED", False)


@pytest.fixture(autouse=True)
def disable_external_startup(monkeypatch):
    """Prevent tests from connecting to real Supabase/Redis/Postgres on startup."""
    monkeypatch.setattr(main_module, "init_supabase", lambda: None)
    monkeypatch.setattr(main_module, "init_redis", AsyncMock())
    monkeypatch.setattr(main_module, "init_postgres", AsyncMock())
    monkeypatch.setattr(main_module, "ping_supabase", AsyncMock(return_value=False))
    monkeypatch.setattr(main_module, "ping_redis", AsyncMock(return_value=False))
    monkeypatch.setattr(main_module, "close_redis", AsyncMock())
    monkeypatch.setattr(main_module, "close_postgres", AsyncMock())
    monkeypatch.setattr(main_module, "close_supabase", lambda: None)
    monkeypatch.setattr(
        "app.core.startup_validation.run_startup_security_checks",
        lambda _settings: None,
    )


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_client() -> TestClient:
    def _override_user() -> dict:
        return TEST_USER

    app.dependency_overrides[get_current_user] = _override_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_document_id() -> UUID:
    return uuid4()


@pytest.fixture(autouse=True)
def mock_services(monkeypatch, sample_document_id):
    """Mock external services for legacy API integration tests."""

    async def mock_upload(self, file, current_user, org_id=None):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        doc = DocumentResponse(
            id=sample_document_id,
            user_id=UUID(TEST_USER["id"]),
            filename=file.filename or "test.pdf",
            title=file.filename or "test.pdf",
            storage_path=f"{TEST_USER['id']}/{sample_document_id}/test.pdf",
            mime_type=file.content_type or "application/pdf",
            size_bytes=100,
            status="uploaded",
            created_at=now,
            updated_at=now,
        )
        return DocumentUploadResponse(document=doc, message="ok")

    async def mock_list(self, user_id: str):
        return DocumentListResponse(items=[], total=0)

    async def mock_get(self, document_id: UUID, user_id: str):
        return None

    async def mock_ingest(self, document_id: UUID, current_user: dict):
        return IngestionResponse(
            document_id=document_id,
            status=IngestionStatus.INDEXED,
            chunks_created=2,
            embeddings_created=2,
            message="ok",
        )

    async def mock_chat(self, *, query, user_id, document_ids=None, top_k=None):
        return ChatResponse(
            answer=f"Answer to: {query} [1]",
            sources=[
                Source(
                    document_id=sample_document_id,
                    chunk_index=0,
                    snippet="Sample snippet",
                    score=0.9,
                )
            ],
            citations=[
                Citation(
                    document_id=sample_document_id,
                    chunk_index=0,
                    snippet="Sample snippet",
                    label="[1]",
                )
            ],
            model="gpt-4o-mini",
            query=query,
        )

    monkeypatch.setattr(DocumentService, "upload_document", mock_upload)
    monkeypatch.setattr(DocumentService, "list_by_user", mock_list)
    monkeypatch.setattr(DocumentService, "get_by_id", mock_get)
    monkeypatch.setattr(IngestionService, "start_ingestion", mock_ingest)
    monkeypatch.setattr(RAGService, "query", mock_chat)
