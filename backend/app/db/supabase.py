"""Supabase client — singleton, async-safe via asyncio.to_thread."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, BinaryIO, Callable, Optional, TypeVar

from supabase import Client, create_client

from app.core.config import settings

T = TypeVar("T")

_client: Optional[Client] = None


@lru_cache
def _build_client() -> Client:
    if not settings.supabase_configured:
        raise RuntimeError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def init_supabase() -> None:
    global _client
    if settings.supabase_configured:
        _client = _build_client()


def close_supabase() -> None:
    global _client
    _client = None
    _build_client.cache_clear()


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


async def run_supabase(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run sync Supabase SDK call without blocking the event loop."""
    return await asyncio.to_thread(fn, *args, **kwargs)


def _storage(client: Client, bucket: str | None = None):
    return client.storage.from_(bucket or settings.SUPABASE_STORAGE_BUCKET)


async def upload_file(
    path: str,
    content: bytes | BinaryIO,
    *,
    bucket: str | None = None,
    content_type: str = "application/octet-stream",
    upsert: bool = False,
) -> dict[str, Any]:
    """Upload a file to Supabase Storage. Returns storage API response data."""
    client = get_supabase()

    def _upload():
        options = {"content-type": content_type, "upsert": str(upsert).lower()}
        return _storage(client, bucket).upload(path, content, file_options=options)

    result = await run_supabase(_upload)
    return result if isinstance(result, dict) else {"path": path}


async def get_signed_url(
    path: str,
    *,
    bucket: str | None = None,
    expires_in: int | None = None,
) -> str:
    """Create a signed download URL for a storage object."""
    client = get_supabase()
    ttl = expires_in or settings.SUPABASE_SIGNED_URL_EXPIRES

    def _sign():
        response = _storage(client, bucket).create_signed_url(path, ttl)
        return response

    result = await run_supabase(_sign)
    if isinstance(result, dict):
        return result.get("signedURL") or result.get("signed_url") or ""
    return str(result)


async def list_files(
    prefix: str = "",
    *,
    bucket: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List objects under a storage prefix."""
    client = get_supabase()

    def _list():
        return _storage(client, bucket).list(
            prefix,
            {"limit": limit, "offset": offset, "sortBy": {"column": "name", "order": "asc"}},
        )

    result = await run_supabase(_list)
    if isinstance(result, list):
        return result
    return []


async def download_file(path: str, *, bucket: str | None = None) -> bytes:
    """Download a file from Supabase Storage."""
    client = get_supabase()

    def _download():
        return _storage(client, bucket).download(path)

    result = await run_supabase(_download)
    if isinstance(result, bytes):
        return result
    if hasattr(result, "read"):
        return result.read()
    return bytes(result)


async def delete_file(path: str, *, bucket: str | None = None) -> None:
    """Remove a file from Supabase Storage."""
    client = get_supabase()

    def _delete():
        return _storage(client, bucket).remove([path])

    await run_supabase(_delete)


async def ping_supabase() -> bool:
    if not settings.supabase_configured:
        return False
    try:
        client = get_supabase()
        await run_supabase(lambda: client.table("documents").select("id").limit(1).execute())
        return True
    except Exception:
        return False
