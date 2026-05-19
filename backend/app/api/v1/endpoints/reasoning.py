"""Graph reasoning REST API — document analysis and cross-document comparison."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.graph_reasoning_agent import GraphReasoningAgent, ReasoningFinding
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.db.supabase import get_supabase, run_supabase
from app.knowledge.confidence import ConfidencePropagator

logger = get_logger(__name__)

router = APIRouter()

DOCUMENTS_TABLE = "documents"


class ReasoningFindingResponse(BaseModel):
    finding_type: str
    severity: str
    title: str
    description: str
    entities_involved: list[str]
    doc_ids_involved: list[str]
    evidence: list[str]
    confidence: float
    recommendation: str


class DocumentAnalysisResponse(BaseModel):
    doc_id: str
    findings: list[ReasoningFindingResponse]
    total_findings: int
    risk_score: int
    analyzed_at: datetime


class CompareDocumentsRequest(BaseModel):
    doc_ids: list[str] = Field(..., min_length=2, max_length=5)


class CompareDocumentsResponse(BaseModel):
    documents_analyzed: int
    common_entities: list[str]
    contradictions: list[ReasoningFindingResponse]
    risk_score: int
    summary: str


def get_reasoning_agent() -> GraphReasoningAgent:
    return GraphReasoningAgent()


async def _assert_document_owner(document_id: UUID, user_id: str) -> None:
    client = get_supabase()

    def _query():
        return (
            client.table(DOCUMENTS_TABLE)
            .select("id")
            .eq("id", str(document_id))
            .eq("user_id", user_id)
            .is_("deleted_at", "null")
            .maybe_single()
            .execute()
        )

    result = await run_supabase(_query)
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )


def _finding_to_response(finding: ReasoningFinding) -> ReasoningFindingResponse:
    return ReasoningFindingResponse(
        finding_type=finding.finding_type,
        severity=finding.severity,
        title=finding.title,
        description=finding.description,
        entities_involved=finding.entities_involved,
        doc_ids_involved=finding.doc_ids_involved,
        evidence=finding.evidence,
        confidence=finding.confidence,
        recommendation=finding.recommendation,
    )


def _validate_doc_id_list(doc_ids: list[str]) -> list[str]:
    if len(doc_ids) < 2 or len(doc_ids) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_ids must contain between 2 and 5 document IDs",
        )
    unique: list[str] = []
    for raw_id in doc_ids:
        try:
            parsed = str(UUID(str(raw_id)))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document id: {raw_id}",
            ) from exc
        if parsed not in unique:
            unique.append(parsed)
    return unique


async def _run_document_analysis(
    doc_id: str,
    user_id: str,
    agent: GraphReasoningAgent,
) -> DocumentAnalysisResponse:
    findings = await agent.analyze_document(doc_id, user_id)
    triples = await agent._load_triples(doc_id, user_id)
    semantic = agent._rows_to_semantic_triples(triples)
    risk_score = ConfidencePropagator().get_risk_score(semantic)["risk_score"]

    return DocumentAnalysisResponse(
        doc_id=doc_id,
        findings=[_finding_to_response(f) for f in findings],
        total_findings=len(findings),
        risk_score=risk_score,
        analyzed_at=datetime.now(timezone.utc),
    )


@router.post(
    "/analyze/{doc_id}",
    response_model=DocumentAnalysisResponse,
    summary="Run graph reasoning analysis on a document",
)
async def analyze_document(
    doc_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    agent: Annotated[GraphReasoningAgent, Depends(get_reasoning_agent)],
) -> DocumentAnalysisResponse:
    user_id = str(current_user["id"])
    doc_id_str = str(doc_id)
    await _assert_document_owner(doc_id, user_id)

    logger.info("Graph reasoning analysis for doc %s (user %s)", doc_id_str, user_id)
    return await _run_document_analysis(doc_id_str, user_id, agent)


@router.post(
    "/compare",
    response_model=CompareDocumentsResponse,
    summary="Compare semantic graphs across documents",
)
async def compare_documents(
    body: CompareDocumentsRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    agent: Annotated[GraphReasoningAgent, Depends(get_reasoning_agent)],
) -> CompareDocumentsResponse:
    user_id = str(current_user["id"])
    doc_ids = _validate_doc_id_list(body.doc_ids)

    for doc_id in doc_ids:
        await _assert_document_owner(UUID(doc_id), user_id)

    logger.info(
        "Graph reasoning compare for %d documents (user %s)",
        len(doc_ids),
        user_id,
    )
    result = await agent.compare_documents(doc_ids, user_id)
    contradictions = result.get("contradictions") or []

    return CompareDocumentsResponse(
        documents_analyzed=int(result.get("documents_analyzed", 0)),
        common_entities=list(result.get("common_entities") or []),
        contradictions=[
            _finding_to_response(f)
            for f in contradictions
            if isinstance(f, ReasoningFinding)
        ],
        risk_score=int(result.get("risk_score", 0)),
        summary=str(result.get("summary") or ""),
    )


@router.get(
    "/findings/{doc_id}",
    response_model=DocumentAnalysisResponse,
    summary="Get reasoning findings for a document (runs analysis)",
)
async def get_document_findings(
    doc_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    agent: Annotated[GraphReasoningAgent, Depends(get_reasoning_agent)],
) -> DocumentAnalysisResponse:
    user_id = str(current_user["id"])
    doc_id_str = str(doc_id)
    await _assert_document_owner(doc_id, user_id)

    logger.info("Graph reasoning findings for doc %s (user %s)", doc_id_str, user_id)
    return await _run_document_analysis(doc_id_str, user_id, agent)
