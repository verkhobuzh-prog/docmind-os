"""Upload allowlists and size limits for document uploads."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.core.config import settings

MAX_DOCUMENT_SIZE = settings.max_document_bytes
MAX_AUDIO_SIZE = settings.max_audio_bytes

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".xlsx",
    ".xls",
    ".csv",
    ".docx",
    ".pptx",
    ".mp3",
    ".mp4",
    ".m4a",
    ".wav",
    ".webm",
    ".ogg",
}

AUDIO_EXTENSIONS = frozenset({".mp3", ".mp4", ".m4a", ".wav", ".webm", ".ogg"})

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "video/mp4",
}

AUDIO_MIME_TYPES = frozenset(
    {
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/x-m4a",
        "audio/wav",
        "audio/x-wav",
        "audio/webm",
        "audio/ogg",
        "video/mp4",
    }
)


def file_extension(filename: str) -> str:
    name = (filename or "").lower()
    if "." not in name:
        return ""
    return name[name.rfind(".") :]


def is_audio_file(ext: str, mime_type: str) -> bool:
    mime = (mime_type or "").lower()
    return ext in AUDIO_EXTENSIONS or mime in AUDIO_MIME_TYPES or mime.startswith("audio/")


def allowed_extensions() -> set[str]:
    base = {e for e in ALLOWED_EXTENSIONS if e not in AUDIO_EXTENSIONS}
    if settings.audio_enabled:
        return base | set(AUDIO_EXTENSIONS)
    return base


def validate_upload(filename: str, mime_type: str, size_bytes: int) -> None:
    ext = file_extension(filename)
    mime = (mime_type or "application/octet-stream").lower()
    audio = is_audio_file(ext, mime)

    if audio and not settings.audio_enabled:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Audio upload requires audio transcription "
                "(AUDIO_TRANSCRIPTION_ENABLED=true and OPENAI_API_KEY)"
            ),
        )

    ext_ok = ext in allowed_extensions()
    mime_ok = mime in ALLOWED_MIME_TYPES

    if not ext_ok and not mime_ok:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {mime_type or filename}",
        )

    max_size = MAX_AUDIO_SIZE if audio else MAX_DOCUMENT_SIZE
    if size_bytes > max_size:
        limit_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {limit_mb}MB",
        )
