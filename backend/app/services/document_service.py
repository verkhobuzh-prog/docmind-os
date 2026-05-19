import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.db.supabase import get_signed_url, get_supabase, run_supabase, upload_file
from app.services.document_enrichment import enrich_document_after_upload
from app.services.document_upload_policy import validate_upload
from app.utils.categorization import is_rag_ingestible
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)

TABLE_NAME = "documents"


def _sanitize_filename(name: str) -> str:
    clean = Path(name).name.strip()
    clean = re.sub(r"[^\w.\- ]", "_", clean)
    return clean or "unnamed"


def _row_to_response(row: dict) -> DocumentResponse:
    return DocumentResponse(
        id=UUID(str(row["id"])),
        org_id=UUID(str(row["org_id"])) if row.get("org_id") else None,
        user_id=UUID(str(row["user_id"])),
        filename=row["filename"],
        title=row["title"],
        storage_path=row["storage_path"],
        mime_type=row.get("mime_type"),
        size_bytes=int(row.get("size_bytes", 0)),
        status=row.get("status", "uploaded"),
        subject=row.get("subject"),
        document_type=row.get("document_type"),
        metadata=row.get("metadata") or {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class DocumentService:
    async def upload_document(
        self,
        file: UploadFile,
        current_user: dict,
        org_id: UUID | None = None,
    ) -> DocumentUploadResponse:
        if not settings.supabase_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service is not configured",
            )

        content = await file.read()
        size_bytes = len(content)
        if size_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file",
            )
        mime_type = file.content_type or "application/octet-stream"
        validate_upload(file.filename or "", mime_type, size_bytes)

        user_id = str(current_user["id"])
        document_id = uuid4()
        filename = _sanitize_filename(file.filename or "unnamed")
        title = filename
        storage_path = f"{user_id}/{document_id}/{filename}"

        await upload_file(
            storage_path,
            content,
            content_type=mime_type,
        )

        now = datetime.now(timezone.utc)
        row = {
            "id": str(document_id),
            "org_id": str(org_id) if org_id else None,
            "user_id": user_id,
            "filename": filename,
            "title": title,
            "storage_path": storage_path,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "status": "uploaded",
            "metadata": {"original_filename": file.filename},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        client = get_supabase()

        def _insert():
            return client.table(TABLE_NAME).insert(row).execute()

        result = await run_supabase(_insert)
        inserted = result.data[0]

        enrichment = await enrich_document_after_upload(
            document_id=document_id,
            user_id=user_id,
            content=content,
            filename=filename,
            mime_type=mime_type,
            title=title,
        )
        inserted["subject"] = enrichment["subject"]
        inserted["document_type"] = enrichment["document_type"]
        inserted.setdefault("metadata", {})
        if isinstance(inserted["metadata"], dict):
            inserted["metadata"].update(
                {
                    "is_duplicate": enrichment["is_duplicate"],
                    "duplicate_of": enrichment.get("duplicate_of"),
                    "media": enrichment.get("media"),
                }
            )

        if not is_rag_ingestible(mime_type):
            await self._mark_media_catalogued(document_id, user_id)

        document = _row_to_response(inserted)

        signed_url: str | None = None
        try:
            signed_url = await get_signed_url(storage_path)
        except Exception:
            signed_url = None

        msg = "Document uploaded successfully"
        if enrichment.get("is_duplicate"):
            msg = "Document uploaded (marked as duplicate)"
        if not is_rag_ingestible(mime_type):
            msg = "Media uploaded (catalogued; text search not applied)"

        return DocumentUploadResponse(
            document=document,
            signed_url=signed_url or None,
            message=msg,
        )

    async def should_auto_ingest(self, mime_type: str) -> bool:
        return is_rag_ingestible(mime_type)

    async def _mark_media_catalogued(self, document_id: UUID, user_id: str) -> None:
        client = get_supabase()
        now = datetime.now(timezone.utc).isoformat()

        def _upd():
            return (
                client.table(TABLE_NAME)
                .update({"status": "indexed", "updated_at": now})
                .eq("id", str(document_id))
                .eq("user_id", user_id)
                .execute()
            )

        await run_supabase(_upd)

    async def list_by_user(self, user_id: str) -> DocumentListResponse:
        if not settings.supabase_configured:
            return DocumentListResponse(items=[], total=0)

        client = get_supabase()

        def _query():
            return (
                client.table(TABLE_NAME)
                .select("*", count="exact")
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .order("created_at", desc=True)
                .execute()
            )

        result = await run_supabase(_query)
        items = [_row_to_response(row) for row in result.data]
        total = result.count if result.count is not None else len(items)
        return DocumentListResponse(items=items, total=total)

    async def get_by_id(self, document_id: UUID, user_id: str) -> DocumentResponse | None:
        if not settings.supabase_configured:
            return None

        client = get_supabase()

        def _query():
            return (
                client.table(TABLE_NAME)
                .select("*")
                .eq("id", str(document_id))
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .maybe_single()
                .execute()
            )

        result = await run_supabase(_query)
        if result.data is None:
            return None
        return _row_to_response(result.data)

    async def delete_document(self, document_id: str, user_id: str) -> None:
        if not settings.supabase_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service is not configured",
            )

        client = get_supabase()

        def _update():
            return (
                client.table(TABLE_NAME)
                .update({"deleted_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", document_id)
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .execute()
            )

        result = await run_supabase(_update)
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
