"""Pytest fixtures for DocMind OS API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import DEV_USER_ID, get_current_user
from app.main import app
import app.main as main_module
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
    """Mock external services (Supabase, OpenAI) for unit tests."""

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

    async def mock_chat(self, query, current_user, document_ids=None, top_k=None):
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
