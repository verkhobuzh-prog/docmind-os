"""Unit tests for GraphReasoningAgent and reasoning API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.graph_reasoning_agent import GraphReasoningAgent, ReasoningFinding


def test_reasoning_finding_dataclass():
    finding = ReasoningFinding(
        finding_type="contradiction",
        severity="high",
        title="Test contradiction",
        description="Conflicting objects detected.",
        entities_involved=["Acme Corp"],
        doc_ids_involved=["doc-a", "doc-b"],
        evidence=["quote a", "quote b"],
        confidence=0.75,
        recommendation="Review both documents.",
    )

    assert finding.finding_type == "contradiction"
    assert finding.severity == "high"
    assert finding.title == "Test contradiction"
    assert finding.description == "Conflicting objects detected."
    assert finding.entities_involved == ["Acme Corp"]
    assert finding.doc_ids_involved == ["doc-a", "doc-b"]
    assert finding.evidence == ["quote a", "quote b"]
    assert finding.confidence == 0.75
    assert finding.recommendation == "Review both documents."


def test_detect_confidence_anomalies_high_risk():
    agent = GraphReasoningAgent()
    triples = [
        {
            "confidence": 0.3,
            "doc_id": str(uuid4()),
            "evidence_quote": f"low evidence {i}",
            "validation_status": "auto-extracted",
        }
        for i in range(8)
    ] + [
        {
            "confidence": 0.9,
            "doc_id": str(uuid4()),
            "evidence_quote": f"high evidence {i}",
            "validation_status": "auto-extracted",
        }
        for i in range(2)
    ]

    findings = agent._detect_confidence_anomalies(triples)

    assert len(findings) >= 1
    cluster = next(f for f in findings if "low-confidence" in f.title.lower())
    assert cluster.severity == "high"
    assert cluster.finding_type == "anomaly"


def test_detect_confidence_anomalies_clean():
    agent = GraphReasoningAgent()
    triples = [
        {
            "confidence": 0.9,
            "doc_id": str(uuid4()),
            "evidence_quote": f"strong evidence {i}",
            "validation_status": "auto-extracted",
        }
        for i in range(5)
    ]

    findings = agent._detect_confidence_anomalies(triples)

    assert findings == []


@pytest.mark.asyncio
async def test_detect_temporal_conflicts(monkeypatch):
    agent = GraphReasoningAgent()
    doc_a = str(uuid4())
    doc_b = str(uuid4())
    triples = [
        {
            "subject": "Acme Corp",
            "predicate": "OWNS",
            "object_": "Building A",
            "doc_id": doc_a,
            "confidence": 0.8,
            "evidence_quote": "Acme owns Building A.",
        },
        {
            "subject": "Acme Corp",
            "predicate": "OWNS",
            "object_": "Building B",
            "doc_id": doc_b,
            "confidence": 0.7,
            "evidence_quote": "Acme owns Building B.",
        },
    ]

    async def mock_fetch(_user_id: str, subject: str, predicate: str) -> list[dict]:
        assert subject == "Acme Corp"
        assert predicate == "OWNS"
        return triples

    monkeypatch.setattr(agent, "_fetch_triples_by_subject_predicate", mock_fetch)
    monkeypatch.setattr(
        agent._provenance,
        "_get_user_doc_ids",
        AsyncMock(return_value=[doc_a, doc_b]),
    )

    findings = await agent._detect_temporal_conflicts(triples[:1], "test-user-id")

    assert len(findings) >= 1
    contradiction = next(f for f in findings if f.finding_type == "contradiction")
    assert contradiction.severity == "high"
    assert "Acme Corp" in contradiction.entities_involved
    assert doc_a in contradiction.doc_ids_involved
    assert doc_b in contradiction.doc_ids_involved
    assert len(contradiction.evidence) >= 1


@pytest.mark.asyncio
async def test_analyze_document_no_triples(monkeypatch):
    agent = GraphReasoningAgent()
    monkeypatch.setattr(agent, "_load_triples", AsyncMock(return_value=[]))

    findings = await agent.analyze_document("doc-id", "user-id")

    assert findings == []


def test_reasoning_endpoint_no_auth(client, sample_document_id):
    response = client.get(f"/api/v1/reasoning/findings/{sample_document_id}")

    assert response.status_code == 401


def test_reasoning_analyze_endpoint(auth_client, sample_document_id, monkeypatch):
    async def mock_assert_owner(document_id, user_id: str) -> None:
        assert str(document_id) == str(sample_document_id)
        assert user_id

    mock_agent = MagicMock()
    mock_agent.analyze_document = AsyncMock(return_value=[])
    mock_agent._load_triples = AsyncMock(return_value=[])
    mock_agent._rows_to_semantic_triples = MagicMock(return_value=[])

    monkeypatch.setattr(
        "app.api.v1.endpoints.reasoning._assert_document_owner",
        mock_assert_owner,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.reasoning.get_reasoning_agent",
        lambda: mock_agent,
    )

    response = auth_client.post(f"/api/v1/reasoning/analyze/{sample_document_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["doc_id"] == str(sample_document_id)
    assert body["findings"] == []
    assert body["total_findings"] == 0
    assert body["risk_score"] == 0
    assert "analyzed_at" in body
