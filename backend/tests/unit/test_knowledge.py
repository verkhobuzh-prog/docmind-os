"""Unit tests for the knowledge layer (ontology, extraction, API)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.knowledge.ontology import (
    EntityType,
    ProvenanceRecord,
    RelationType,
    SemanticTriple,
)
from app.utils.triple_extractor import TripleExtractor

EXPECTED_ENTITY_TYPES = {
    "PERSON",
    "ORGANIZATION",
    "AGREEMENT",
    "ASSET",
    "LOCATION",
    "LEGAL_CASE",
    "FINANCIAL_RECORD",
    "EVENT",
    "POLICY",
    "PROJECT",
}

EXPECTED_RELATION_TYPES = {
    "SIGNED_BY",
    "REFERENCES",
    "SUPERSEDES",
    "CANCELLED_BY",
    "PART_OF",
    "OWNS",
    "RELATED_TO",
    "APPROVED_BY",
    "TERMINATED_BY",
    "ASSOCIATED_WITH",
}


def test_ontology_entity_types():
    assert len(EntityType) == 10
    assert {member.value for member in EntityType} == EXPECTED_ENTITY_TYPES


def test_ontology_relation_types():
    assert len(RelationType) == 10
    assert {member.value for member in RelationType} == EXPECTED_RELATION_TYPES


def test_semantic_triple_creation():
    triple = SemanticTriple(
        subject="Acme LLC",
        subject_type=EntityType.ORGANIZATION,
        predicate=RelationType.OWNS,
        object_="Warehouse",
        object_type=EntityType.ASSET,
        confidence=0.92,
        evidence_quote="Acme LLC owns the warehouse.",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=None,
    )

    assert triple.subject == "Acme LLC"
    assert triple.subject_type is EntityType.ORGANIZATION
    assert triple.predicate is RelationType.OWNS
    assert triple.object_ == "Warehouse"
    assert triple.object_type is EntityType.ASSET
    assert triple.confidence == 0.92
    assert triple.evidence_quote == "Acme LLC owns the warehouse."
    assert triple.valid_from is not None
    assert triple.valid_to is None
    assert triple.provenance is None


def test_provenance_record_defaults():
    record = ProvenanceRecord(
        doc_id="doc-1",
        chunk_id="chunk-1",
        page_num=2,
        extraction_model="gpt-4o-mini",
        extracted_at=datetime.now(timezone.utc),
        confidence=0.85,
        evidence_quote="Sample evidence.",
    )

    assert record.validation_status == "auto-extracted"


@pytest.mark.asyncio
async def test_triple_extractor_disabled(monkeypatch):
    monkeypatch.setattr("app.utils.triple_extractor.settings.TRIPLE_EXTRACTION_ENABLED", False)

    extractor = TripleExtractor()
    result = await extractor.extract(
        chunk_text="Alice owns Acme.",
        doc_id="doc-1",
        chunk_id="chunk-1",
    )

    assert result == []


def test_knowledge_entities_no_graph(auth_client, monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.knowledge.settings.GRAPH_DB_ENABLED", False)

    response = auth_client.get("/api/v1/knowledge/entities/TestCorp")

    assert response.status_code == 503
    assert response.json()["error"] == "Graph DB not configured"


def test_knowledge_triples_endpoint(auth_client, sample_document_id, monkeypatch):
    async def mock_assert_owner(document_id, user_id: str) -> None:
        assert str(document_id) == str(sample_document_id)
        assert user_id

    async def mock_run_supabase(fn):
        return MagicMock(data=[])

    monkeypatch.setattr(
        "app.api.v1.endpoints.knowledge._assert_document_owner",
        mock_assert_owner,
    )
    monkeypatch.setattr("app.api.v1.endpoints.knowledge.get_supabase", lambda: MagicMock())
    monkeypatch.setattr("app.api.v1.endpoints.knowledge.run_supabase", mock_run_supabase)

    response = auth_client.get(f"/api/v1/knowledge/documents/{sample_document_id}/triples")

    assert response.status_code == 200
    body = response.json()
    assert body["doc_id"] == str(sample_document_id)
    assert body["triples"] == []
    assert body["total"] == 0
