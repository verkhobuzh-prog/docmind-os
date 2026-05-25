"""Integration tests for ingestion HTTP endpoint + queue fallback."""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestIngestionEndpointPipeline:
    def test_async_ingest_returns_queued_when_redis_available(
        self, auth_client, sample_document_id, patch_redis
    ):
        response = auth_client.post(f"/api/v1/documents/{sample_document_id}/ingest")
        assert response.status_code == 202
        data = response.json()
        assert data["message"] == "queued"
        assert data["status"] == "parsing"

    def test_async_ingest_falls_back_when_redis_unavailable(
        self, auth_client, sample_document_id, monkeypatch
    ):
        monkeypatch.setattr(
            "app.services.job_queue.get_redis",
            lambda: (_ for _ in ()).throw(RuntimeError("redis down")),
        )

        response = auth_client.post(f"/api/v1/documents/{sample_document_id}/ingest")
        assert response.status_code == 202
        data = response.json()
        assert data["message"] == "processing"

    def test_sync_ingest_runs_service_directly(self, auth_client, sample_document_id):
        response = auth_client.post(
            f"/api/v1/documents/{sample_document_id}/ingest",
            params={"sync": "true"},
        )
        assert response.status_code in (200, 202)
        data = response.json()
        assert data["status"] == "indexed"
        assert data["chunks_created"] >= 1

    def test_queue_stats_requires_admin(self, auth_client):
        response = auth_client.get("/api/v1/documents/ingestion/queue/stats")
        assert response.status_code == 403

    def test_queue_stats_for_admin(self, admin_client, patch_redis, sample_document_id):
        admin_client.post(f"/api/v1/documents/{sample_document_id}/ingest")

        response = admin_client.get("/api/v1/documents/ingestion/queue/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["queued"] >= 1
