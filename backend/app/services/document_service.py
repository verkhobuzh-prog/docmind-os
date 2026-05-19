import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.db.supabase import get_signed_url, get_supabase, run_supabase, upload_file
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)

TABLE_NAME = "documents"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_PREFIXES = (
    "application/pdf",
    "application/vnd.",
    "application/msword",
    "application/json",
    "text/",
    "image/",
)


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
        if size_bytes > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES} bytes",
            )

        mime_type = file.content_type or "application/octet-stream"
        if not any(mime_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {mime_type}",
            )

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
        document = _row_to_response(result.data[0])

        signed_url: str | None = None
        try:
            signed_url = await get_signed_url(storage_path)
        except Exception:
            signed_url = None

        return DocumentUploadResponse(
            document=document,
            signed_url=signed_url or None,
            message="Document uploaded successfully",
        )

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
