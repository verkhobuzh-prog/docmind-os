"""Knowledge graph service — FalkorDB persistence and traversal."""

from __future__ import annotations

import asyncio
from typing import Any

from falkordb.graph import Graph

from app.core.config import settings
from app.core.logging import get_logger
from app.db.graph import get_graph, ping_graph
from app.db.supabase import get_supabase, run_supabase
from app.knowledge.ontology import SemanticTriple

logger = get_logger(__name__)

_EMPTY_GRAPH: dict[str, list] = {"nodes": [], "edges": []}

_UPSERT_QUERY = """
MERGE (s:Entity {name: $subject, type: $subject_type})
MERGE (o:Entity {name: $object, type: $object_type})
MERGE (s)-[r:RELATION {type: $predicate}]->(o)
ON CREATE SET r.confidence = $confidence, r.doc_id = $doc_id,
              r.evidence = $evidence_quote, r.created_at = timestamp()
ON MATCH SET r.confidence = CASE WHEN r.confidence < $confidence
                                 THEN $confidence ELSE r.confidence END
"""


class GraphService:
    """FalkorDB-backed knowledge graph operations."""

    def _graph(self) -> Graph | None:
        if not settings.graph_configured:
            return None
        return get_graph(settings.GRAPH_DB_NAME)

    async def upsert_triples(self, triples: list[SemanticTriple], doc_id: str) -> int:
        if not triples:
            return 0

        written = 0
        if settings.graph_configured:
            graph = self._graph()
            if graph is None:
                logger.debug("Graph DB unavailable; skipping FalkorDB upsert")
            else:
                for triple in triples:
                    try:
                        await asyncio.to_thread(self._upsert_one, graph, triple, doc_id)
                        written += 1
                    except Exception as exc:
                        logger.warning(
                            "Failed to upsert triple %s -[%s]-> %s: %s",
                            triple.subject,
                            triple.predicate.value,
                            triple.object_,
                            exc,
                        )
        else:
            logger.debug("Graph DB not configured; skipping FalkorDB upsert")

        saved = await self._persist_triples_to_postgres(triples, doc_id)
        logger.info("Persisted %d triples to Postgres", saved)
        return written

    async def _persist_triples_to_postgres(
        self, triples: list[SemanticTriple], doc_id: str
    ) -> int:
        """Зберігає трійки в semantic_triples таблицю Supabase для аудиту."""
        if not triples:
            return 0

        rows = []
        for t in triples:
            row = {
                "doc_id": doc_id,
                "chunk_id": t.provenance.chunk_id if t.provenance else None,
                "subject": t.subject,
                "subject_type": t.subject_type.value,
                "predicate": t.predicate.value,
                "object_": t.object_,
                "object_type": t.object_type.value,
                "confidence": t.confidence,
                "evidence_quote": t.evidence_quote[:500] if t.evidence_quote else None,
                "valid_from": t.valid_from.isoformat() if t.valid_from else None,
                "valid_to": t.valid_to.isoformat() if t.valid_to else None,
                "extraction_model": t.provenance.extraction_model if t.provenance else None,
                "validation_status": t.provenance.validation_status
                if t.provenance
                else "auto-extracted",
            }
            rows.append(row)

        try:
            client = get_supabase()
            await run_supabase(
                lambda: client.table("semantic_triples").insert(rows).execute()
            )
            return len(rows)
        except Exception as e:
            logger.warning("Failed to persist triples to Postgres: %s", e)
            return 0

    @staticmethod
    def _upsert_one(graph: Graph, triple: SemanticTriple, doc_id: str) -> None:
        graph.query(
            _UPSERT_QUERY,
            {
                "subject": triple.subject,
                "subject_type": triple.subject_type.value,
                "object": triple.object_,
                "object_type": triple.object_type.value,
                "predicate": triple.predicate.value,
                "confidence": triple.confidence,
                "doc_id": doc_id,
                "evidence_quote": triple.evidence_quote,
            },
        )

    async def search_entities(self, entity_name: str, depth: int = 2) -> dict:
        if not settings.graph_configured:
            return dict(_EMPTY_GRAPH)

        graph = self._graph()
        if graph is None:
            return dict(_EMPTY_GRAPH)

        depth = max(1, min(depth, 5))
        try:
            return await asyncio.to_thread(self._search_entities_sync, graph, entity_name, depth)
        except Exception as exc:
            logger.warning("Graph search failed for entity %r: %s", entity_name, exc)
            return dict(_EMPTY_GRAPH)

    @staticmethod
    def _search_entities_sync(graph: Graph, entity_name: str, depth: int) -> dict:
        nodes_by_key: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()

        anchor_result = graph.query(
            """
            MATCH (start:Entity)
            WHERE toLower(start.name) = toLower($entity_name)
            RETURN start
            LIMIT 1
            """,
            {"entity_name": entity_name},
        )
        if not anchor_result.result_set:
            return dict(_EMPTY_GRAPH)

        GraphService._add_node_from_value(anchor_result.result_set[0][0], nodes_by_key)

        path_query = f"""
        MATCH (start:Entity)
        WHERE toLower(start.name) = toLower($entity_name)
        MATCH p = (start)-[rels:RELATION*1..{depth}]-(end:Entity)
        RETURN p
        """
        path_result = graph.query(path_query, {"entity_name": entity_name})
        for row in path_result.result_set or []:
            if not row or row[0] is None:
                continue
            GraphService._accumulate_path(row[0], nodes_by_key, edges, seen_edges)

        return {"nodes": list(nodes_by_key.values()), "edges": edges}

    @staticmethod
    def _add_node_from_value(
        node: Any,
        nodes_by_key: dict[str, dict[str, Any]],
    ) -> str | None:
        props = GraphService._node_properties(node)
        name = str(props.get("name", "")).strip()
        if not name:
            return None
        entity_type = str(props.get("type", "UNKNOWN"))
        key = f"{entity_type}::{name}"
        if key not in nodes_by_key:
            nodes_by_key[key] = {"id": key, "name": name, "type": entity_type}
        return key

    @staticmethod
    def _accumulate_path(
        path: Any,
        nodes_by_key: dict[str, dict[str, Any]],
        edges: list[dict[str, Any]],
        seen_edges: set[tuple[str, str, str]],
    ) -> None:
        path_nodes = path.nodes() if callable(getattr(path, "nodes", None)) else getattr(path, "nodes", [])
        path_edges = path.edges() if callable(getattr(path, "edges", None)) else getattr(path, "edges", [])

        for node in path_nodes or []:
            GraphService._add_node_from_value(node, nodes_by_key)

        for edge in path_edges or []:
            src_key = GraphService._add_node_from_value(edge.src_node, nodes_by_key)
            dest_key = GraphService._add_node_from_value(edge.dest_node, nodes_by_key)
            if not src_key or not dest_key:
                continue
            rel_type = str(edge.properties.get("type") or edge.relation or "RELATED_TO")
            edge_key = (src_key, dest_key, rel_type)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "source": src_key,
                    "target": dest_key,
                    "type": rel_type,
                    "confidence": edge.properties.get("confidence"),
                }
            )

    @staticmethod
    def _node_properties(node: Any) -> dict[str, Any]:
        if isinstance(node, dict):
            return node
        if hasattr(node, "properties"):
            return dict(node.properties)
        return {}

    async def get_related_documents(self, entity_name: str) -> list[str]:
        if not settings.graph_configured:
            return []

        graph = self._graph()
        if graph is None:
            return []

        try:
            return await asyncio.to_thread(self._get_related_documents_sync, graph, entity_name)
        except Exception as exc:
            logger.warning("Failed to fetch related documents for %r: %s", entity_name, exc)
            return []

    @staticmethod
    def _get_related_documents_sync(graph: Graph, entity_name: str) -> list[str]:
        query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) = toLower($entity_name)
        MATCH (e)-[r:RELATION]-()
        WHERE r.doc_id IS NOT NULL
        RETURN DISTINCT r.doc_id AS doc_id
        """
        result = graph.query(query, {"entity_name": entity_name})
        doc_ids: list[str] = []
        for row in result.result_set or []:
            if not row:
                continue
            doc_id = row[0]
            if doc_id is not None:
                doc_ids.append(str(doc_id))
        return doc_ids

    async def ping(self) -> bool:
        if not settings.graph_configured:
            return False
        return await ping_graph()
