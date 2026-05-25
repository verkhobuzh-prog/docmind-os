from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger
from app.core.telemetry import traced_span
from app.core.state_machine import DocumentEvent, DocumentState
from app.db.supabase import download_file, get_supabase, run_supabase
from app.schemas.ingestion import ChunkMetadata, IngestionResponse, IngestionStatus
from app.services.lifecycle_service import get_lifecycle_service
from app.utils.chunking import chunk_text
from app.utils.embeddings import embed_texts
from app.utils.parsers import parse_document

logger = get_logger("Doc-Hub.ingestion")

DOCUMENTS_TABLE = "documents"
CHUNKS_TABLE = "document_chunks"


async def _lifecycle_step(
    lifecycle,
    doc_id: str,
    user_id: str,
    event: DocumentEvent,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """Run a lifecycle transition; never raise — ingestion must continue."""
    try:
        await lifecycle.transition(
            doc_id,
            user_id,
            event,
            error_code=error_code,
            error_message=error_message,
        )
    except Exception as exc:
        logger.warning(
            "Lifecycle transition %s failed for document %s: %s",
            event.value,
            doc_id,
            exc,
        )


class IngestionService:
    async def start_ingestion(
        self,
        document_id: UUID,
        current_user: dict,
    ) -> IngestionResponse:
        started_at = datetime.now(timezone.utc)
        user_id = str(current_user["id"])
        doc_id = str(document_id)
        lifecycle = get_lifecycle_service()

        if not settings.supabase_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ingestion service is not configured",
            )

        doc = await self._get_document(document_id, user_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        current_state = await lifecycle.get_state(doc_id)
        if current_state == DocumentState.PARSING:
            return IngestionResponse(
                document_id=document_id,
                status=IngestionStatus.PARSING,
                message="Ingestion already in progress",
                started_at=started_at,
            )

        failure_event = DocumentEvent.FAIL_PARSE

        with traced_span(
            "ingestion.run",
            {
                "document.id": doc_id,
                "user.id": user_id,
            },
        ) as root_span:
            try:
                await _lifecycle_step(lifecycle, doc_id, user_id, DocumentEvent.VALIDATE)
                await _lifecycle_step(lifecycle, doc_id, user_id, DocumentEvent.QUEUE)
                await _lifecycle_step(lifecycle, doc_id, user_id, DocumentEvent.START_PARSE)

                with traced_span("ingestion.parse", {"document.id": doc_id}):
                    raw = await download_file(doc["storage_path"])
                    parsed = await asyncio.to_thread(
                        parse_document,
                        raw,
                        doc.get("mime_type") or "application/octet-stream",
                        doc.get("filename") or "",
                    )

                if not parsed.text.strip():
                    raise ValueError("No extractable text in document")

                root_span.set_attribute("parser", parsed.parser)
                root_span.set_attribute("text.length", len(parsed.text))

                await _lifecycle_step(lifecycle, doc_id, user_id, DocumentEvent.FINISH_PARSE)

                with traced_span("ingestion.chunk"):
                    chunks = chunk_text(parsed.text)
                if not chunks:
                    raise ValueError("Chunking produced no content")

                root_span.set_attribute("chunks.count", len(chunks))

                failure_event = DocumentEvent.FAIL_EMBED
                await _lifecycle_step(lifecycle, doc_id, user_id, DocumentEvent.START_EMBED)

                with traced_span("ingestion.embed", {"chunks.count": len(chunks)}):
                    embeddings = await embed_texts(chunks)
                embeddings_count = sum(1 for e in embeddings if e is not None)

                await _lifecycle_step(lifecycle, doc_id, user_id, DocumentEvent.FINISH_EMBED)

                chunk_rows = self._build_chunk_rows(
                    document_id=document_id,
                    chunks=chunks,
                    parser=parsed.parser,
                    doc_metadata=parsed.metadata,
                )

                await _lifecycle_step(lifecycle, doc_id, user_id, DocumentEvent.START_GRAPH)
                try:
                    if settings.TRIPLE_EXTRACTION_ENABLED:
                        from app.services.graph_service import GraphService
                        from app.utils.triple_extractor import TripleExtractor

                        extractor = TripleExtractor()
                        graph_svc = GraphService()

                        for chunk in chunk_rows:
                            triples = await extractor.extract(
                                chunk_text=chunk["content"],
                                doc_id=doc_id,
                                chunk_id=str(chunk["id"]),
                                page_num=chunk.get("metadata", {}).get("page_num"),
                            )
                            if triples:
                                await graph_svc.upsert_triples(triples, doc_id=doc_id)
                                logger.info(
                                    "Extracted %d triples from chunk %s",
                                    len(triples),
                                    chunk["id"],
                                )
                    await _lifecycle_step(lifecycle, doc_id, user_id, DocumentEvent.FINISH_GRAPH)
                except Exception as exc:
                    logger.warning(
                        "Triple extraction / graph upsert failed for document %s: %s",
                        document_id,
                        exc,
                    )
                    await _lifecycle_step(
                        lifecycle,
                        doc_id,
                        user_id,
                        DocumentEvent.FAIL_GRAPH,
                        error_message=str(exc),
                    )

                with traced_span("ingestion.upsert"):
                    await self._delete_existing_chunks(document_id)
                    await self._insert_chunk_rows(chunk_rows, embeddings=embeddings)

                await _lifecycle_step(lifecycle, doc_id, user_id, DocumentEvent.COMPLETE)

                await self._patch_metadata(
                    document_id,
                    {
                        "ingestion": {
                            "parser": parsed.parser,
                            "chunks": len(chunks),
                            "embeddings": embeddings_count,
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    },
                )

                return IngestionResponse(
                    document_id=document_id,
                    status=IngestionStatus.INDEXED,
                    chunks_created=len(chunks),
                    embeddings_created=embeddings_count,
                    message="Document ingested successfully",
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                )

            except HTTPException:
                raise
            except Exception as exc:
                logger.exception("Ingestion failed for document %s", document_id)
                error_code = (
                    "EMBED_ERROR"
                    if failure_event == DocumentEvent.FAIL_EMBED
                    else "PARSE_ERROR"
                )
                await _lifecycle_step(
                    lifecycle,
                    doc_id,
                    user_id,
                    failure_event,
                    error_code=error_code,
                    error_message=str(exc),
                )
                await self._patch_metadata(
                    document_id,
                    {"ingestion_error": str(exc)},
                )
                return IngestionResponse(
                    document_id=document_id,
                    status=IngestionStatus.FAILED,
                    message="Ingestion failed",
                    error=str(exc),
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                )

    async def _get_document(self, document_id: UUID, user_id: str) -> dict | None:
        client = get_supabase()

        def _query():
            return (
                client.table(DOCUMENTS_TABLE)
                .select("*")
                .eq("id", str(document_id))
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .maybe_single()
                .execute()
            )

        result = await run_supabase(_query)
        return result.data

    async def _update_document_status(
        self,
        document_id: UUID,
        status: IngestionStatus,
        extra_metadata: dict | None = None,
    ) -> None:
        client = get_supabase()
        payload: dict = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if extra_metadata:
            doc = await self._get_document_raw(document_id)
            meta = (doc or {}).get("metadata") or {}
            if isinstance(meta, dict):
                meta.update(extra_metadata)
                payload["metadata"] = meta

        def _update():
            return (
                client.table(DOCUMENTS_TABLE)
                .update(payload)
                .eq("id", str(document_id))
                .execute()
            )

        await run_supabase(_update)

    async def _patch_metadata(
        self,
        document_id: UUID,
        extra_metadata: dict,
    ) -> None:
        """Merge metadata without changing document status (lifecycle owns status)."""
        doc = await self._get_document_raw(document_id)
        meta = (doc or {}).get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        meta.update(extra_metadata)
        client = get_supabase()
        payload = {
            "metadata": meta,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        def _update():
            return (
                client.table(DOCUMENTS_TABLE)
                .update(payload)
                .eq("id", str(document_id))
                .execute()
            )

        await run_supabase(_update)

    async def _get_document_raw(self, document_id: UUID) -> dict | None:
        client = get_supabase()

        def _query():
            return (
                client.table(DOCUMENTS_TABLE)
                .select("metadata")
                .eq("id", str(document_id))
                .maybe_single()
                .execute()
            )

        result = await run_supabase(_query)
        return result.data

    async def _delete_existing_chunks(self, document_id: UUID) -> None:
        client = get_supabase()

        def _delete():
            return (
                client.table(CHUNKS_TABLE)
                .delete()
                .eq("document_id", str(document_id))
                .execute()
            )

        await run_supabase(_delete)

    def _build_chunk_rows(
        self,
        *,
        document_id: UUID,
        chunks: list[str],
        parser: str,
        doc_metadata: dict,
    ) -> list[dict]:
        rows: list[dict] = []
        for i, content in enumerate(chunks):
            meta = ChunkMetadata(
                chunk_index=i,
                parser=parser,
                token_count=len(content.split()),
                source=doc_metadata.get("format"),
                extra={"document_metadata": doc_metadata},
            )
            metadata = meta.model_dump(exclude_none=True)
            if meta.page is not None:
                metadata["page_num"] = meta.page
            rows.append(
                {
                    "id": str(uuid4()),
                    "document_id": str(document_id),
                    "chunk_index": i,
                    "content": content,
                    "metadata": metadata,
                }
            )
        return rows

    async def _insert_chunk_rows(
        self,
        rows: list[dict],
        *,
        embeddings: list[list[float] | None],
    ) -> None:
        client = get_supabase()
        for i, row in enumerate(rows):
            if i < len(embeddings) and embeddings[i] is not None:
                row["embedding"] = embeddings[i]

        def _insert():
            return client.table(CHUNKS_TABLE).insert(rows).execute()

        await run_supabase(_insert)


def get_ingestion_service() -> IngestionService:
    return IngestionService()
