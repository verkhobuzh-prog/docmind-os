"""Knowledge Graph REST API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.db.supabase import get_supabase, run_supabase
from app.knowledge.confidence import ConfidencePropagator
from app.knowledge.ontology import EntityType, ProvenanceRecord, RelationType, SemanticTriple
from app.services.graph_service import GraphService
from app.services.provenance_service import ProvenanceService

logger = get_logger(__name__)

router = APIRouter()

DOCUMENTS_TABLE = "documents"
TRIPLES_TABLE = "semantic_triples"
_MAX_RISK_ANALYSIS_DOCS = 20


class RiskAnalysisRequest(BaseModel):
    text: str = ""
    doc_ids: list[str] | None = None


def get_graph_service() -> GraphService:
    return GraphService()


def get_provenance_service() -> ProvenanceService:
    return ProvenanceService()


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


async def _count_user_triples(user_id: str) -> int:
    client = get_supabase()

    def _count():
        docs = (
            client.table(DOCUMENTS_TABLE)
            .select("id")
            .eq("user_id", user_id)
            .is_("deleted_at", "null")
            .execute()
        )
        doc_ids = [row["id"] for row in (docs.data or [])]
        if not doc_ids:
            return 0
        result = (
            client.table(TRIPLES_TABLE)
            .select("id", count="exact")
            .in_("doc_id", doc_ids)
            .execute()
        )
        return int(result.count or 0)

    return await run_supabase(_count)


async def _get_recent_user_doc_ids(user_id: str, limit: int = _MAX_RISK_ANALYSIS_DOCS) -> list[str]:
    client = get_supabase()

    def _query():
        return (
            client.table(DOCUMENTS_TABLE)
            .select("id")
            .eq("user_id", user_id)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    result = await run_supabase(_query)
    return [str(row["id"]) for row in (result.data or [])]


def _parse_entity_type(value: str | None) -> EntityType:
    try:
        return EntityType(value or "")
    except ValueError:
        return EntityType.EVENT


def _parse_relation_type(value: str | None) -> RelationType:
    try:
        return RelationType(value or "")
    except ValueError:
        return RelationType.RELATED_TO


def _row_to_semantic_triple(row: dict) -> SemanticTriple:
    validation_status = str(row.get("validation_status") or "auto-extracted")
    provenance = ProvenanceRecord(
        doc_id=str(row.get("doc_id", "")),
        chunk_id=str(row.get("chunk_id") or ""),
        page_num=None,
        extraction_model=str(row.get("extraction_model") or "unknown"),
        extracted_at=datetime.now(timezone.utc),
        confidence=float(row.get("confidence", 0.0)),
        evidence_quote=str(row.get("evidence_quote") or ""),
        validation_status=validation_status,
    )
    return SemanticTriple(
        subject=str(row["subject"]),
        subject_type=_parse_entity_type(row.get("subject_type")),
        predicate=_parse_relation_type(row.get("predicate")),
        object_=str(row.get("object_") or row.get("object") or ""),
        object_type=_parse_entity_type(row.get("object_type")),
        confidence=float(row.get("confidence", 0.0)),
        evidence_quote=str(row.get("evidence_quote") or ""),
        provenance=provenance,
    )


@router.get(
    "/entities/{entity_name}",
    summary="Search knowledge graph around an entity",
)
async def get_entity_graph(
    entity_name: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    graph_service: Annotated[GraphService, Depends(get_graph_service)],
    depth: Annotated[int, Query(ge=1, le=5)] = 2,
) -> dict:
    _ = current_user
    if not settings.graph_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph DB not configured",
        )

    graph = await graph_service.search_entities(entity_name, depth=depth)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    return {
        "entity": entity_name,
        "depth": depth,
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


@router.get(
    "/documents/{doc_id}/triples",
    summary="List semantic triples extracted from a document",
)
async def get_document_triples(
    doc_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    user_id = str(current_user["id"])
    await _assert_document_owner(doc_id, user_id)

    client = get_supabase()

    def _query():
        return (
            client.table(TRIPLES_TABLE)
            .select("*")
            .eq("doc_id", str(doc_id))
            .order("created_at", desc=True)
            .execute()
        )

    result = await run_supabase(_query)
    triples = result.data or []
    return {
        "doc_id": str(doc_id),
        "triples": triples,
        "total": len(triples),
    }


@router.get(
    "/stats",
    summary="Knowledge graph and triple extraction statistics",
)
async def get_knowledge_stats(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    user_id = str(current_user["id"])
    try:
        total_triples = await _count_user_triples(user_id)
    except Exception as exc:
        logger.warning("Failed to count semantic triples for user %s: %s", user_id, exc)
        total_triples = 0

    return {
        "total_triples_in_db": total_triples,
        "graph_enabled": settings.graph_configured,
        "triple_extraction_enabled": settings.TRIPLE_EXTRACTION_ENABLED,
    }


@router.get(
    "/provenance/entity/{entity_name}",
    summary="Provenance sources for an entity across user documents",
)
async def get_entity_provenance(
    entity_name: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    provenance_service: Annotated[ProvenanceService, Depends(get_provenance_service)],
    min_confidence: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
) -> dict:
    user_id = str(current_user["id"])
    sources = await provenance_service.get_entity_provenance(entity_name, user_id)
    if min_confidence > 0.0:
        sources = [
            s for s in sources if float(s.get("confidence", 0.0)) >= min_confidence
        ]
    return {
        "entity": entity_name,
        "sources": sources,
        "total": len(sources),
    }


@router.get(
    "/provenance/confidence-summary",
    summary="Confidence and validation summary for user triples",
)
async def get_confidence_summary(
    current_user: Annotated[dict, Depends(get_current_user)],
    provenance_service: Annotated[ProvenanceService, Depends(get_provenance_service)],
) -> dict:
    user_id = str(current_user["id"])
    return await provenance_service.get_confidence_summary(user_id)


@router.patch(
    "/triples/{triple_id}/dispute",
    summary="Mark a semantic triple as disputed",
)
async def dispute_triple(
    triple_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    provenance_service: Annotated[ProvenanceService, Depends(get_provenance_service)],
) -> dict:
    user_id = str(current_user["id"])
    success = await provenance_service.mark_triple_disputed(str(triple_id), user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triple not found",
        )
    return {"success": True, "triple_id": str(triple_id)}


@router.post(
    "/risk-analysis",
    summary="Semantic risk analysis over document triples",
)
async def analyze_risk(
    body: RiskAnalysisRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    provenance_service: Annotated[ProvenanceService, Depends(get_provenance_service)],
) -> dict:
    _ = body.text
    user_id = str(current_user["id"])

    if body.doc_ids:
        doc_ids: list[str] = []
        for raw_id in body.doc_ids[:_MAX_RISK_ANALYSIS_DOCS]:
            try:
                doc_uuid = UUID(str(raw_id))
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid document id: {raw_id}",
                ) from exc
            await _assert_document_owner(doc_uuid, user_id)
            doc_ids.append(str(doc_uuid))
    else:
        doc_ids = await _get_recent_user_doc_ids(user_id, limit=_MAX_RISK_ANALYSIS_DOCS)

    triple_rows: list[dict] = []
    for doc_id in doc_ids:
        triple_rows.extend(
            await provenance_service.get_triples_for_document(
                doc_id=doc_id,
                user_id=user_id,
                min_confidence=0.0,
            )
        )

    semantic_triples = [_row_to_semantic_triple(row) for row in triple_rows]
    risk = ConfidencePropagator().get_risk_score(semantic_triples)

    return {
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "explanation": risk["explanation"],
        "low_confidence_triples": risk["low_confidence_triples"],
        "disputed_triples": risk["disputed_triples"],
        "total_triples": risk["total_triples"],
        "analyzed_documents": len(doc_ids),
    }
