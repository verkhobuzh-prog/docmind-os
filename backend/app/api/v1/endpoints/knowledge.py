"""Knowledge Graph REST API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.db.supabase import get_supabase, run_supabase
from app.services.graph_service import GraphService

logger = get_logger(__name__)

router = APIRouter()

DOCUMENTS_TABLE = "documents"
TRIPLES_TABLE = "semantic_triples"


def get_graph_service() -> GraphService:
    return GraphService()


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
