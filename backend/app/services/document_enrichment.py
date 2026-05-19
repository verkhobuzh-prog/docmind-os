"""Post-upload: hash, duplicates, categorization, media metadata."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from app.db.supabase import get_supabase, run_supabase
from app.utils.categorization import categorize_document
from app.utils.content_hash import sha256_hex
from app.utils.media_metadata import extract_media_metadata

DOCUMENTS_TABLE = "documents"


async def enrich_document_after_upload(
    *,
    document_id: UUID,
    user_id: str,
    content: bytes,
    filename: str,
    mime_type: str,
    title: str,
) -> dict[str, Any]:
    """
    Compute catalog fields and duplicate markers. Returns metadata patch for response.
    """
    content_hash = sha256_hex(content)
    category = categorize_document(filename=filename, mime_type=mime_type, title=title)
    media = extract_media_metadata(content, mime_type, filename)

    duplicate_of: Optional[str] = None
    is_duplicate = False
    original = await _find_duplicate_original(user_id, content_hash, str(document_id))
    if original:
        duplicate_of = original
        is_duplicate = True

    metadata_patch: dict[str, Any] = {
        "content_hash": content_hash,
        "categorization": {
            "subject": category.subject,
            "document_type": category.document_type,
            "confidence": category.confidence,
            "method": category.method,
        },
        "media": media,
        "is_duplicate": is_duplicate,
    }
    if duplicate_of:
        metadata_patch["duplicate_of"] = duplicate_of

    await _update_document_row(
        document_id=document_id,
        user_id=user_id,
        content_hash=content_hash,
        subject=category.subject,
        document_type=category.document_type,
        metadata_patch=metadata_patch,
    )

    return {
        "subject": category.subject,
        "document_type": category.document_type,
        "is_duplicate": is_duplicate,
        "duplicate_of": duplicate_of,
        "media": media,
    }


async def _find_duplicate_original(
    user_id: str, content_hash: str, exclude_id: str
) -> Optional[str]:
    client = get_supabase()

    def _q():
        return (
            client.table(DOCUMENTS_TABLE)
            .select("id")
            .eq("user_id", user_id)
            .eq("content_hash", content_hash)
            .neq("id", exclude_id)
            .is_("deleted_at", "null")
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )

    result = await run_supabase(_q)
    if result.data:
        return str(result.data[0]["id"])
    return None


async def _update_document_row(
    *,
    document_id: UUID,
    user_id: str,
    content_hash: str,
    subject: str,
    document_type: str,
    metadata_patch: dict[str, Any],
) -> None:
    client = get_supabase()

    def _get_meta():
        return (
            client.table(DOCUMENTS_TABLE)
            .select("metadata")
            .eq("id", str(document_id))
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

    meta_result = await run_supabase(_get_meta)
    base_meta = (meta_result.data or {}).get("metadata") or {}
    if not isinstance(base_meta, dict):
        base_meta = {}
    merged = {**base_meta, **metadata_patch}

    payload = {
        "content_hash": content_hash,
        "subject": subject,
        "document_type": document_type,
        "metadata": merged,
    }

    def _upd():
        return (
            client.table(DOCUMENTS_TABLE)
            .update(payload)
            .eq("id", str(document_id))
            .eq("user_id", user_id)
            .execute()
        )

    await run_supabase(_upd)
