"""Extract basic metadata from images and video files."""

from __future__ import annotations

from typing import Any


def extract_media_metadata(content: bytes, mime_type: str, filename: str) -> dict[str, Any]:
    mime = (mime_type or "").lower()
    name = (filename or "").lower()
    meta: dict[str, Any] = {"media_kind": "unknown"}

    if mime.startswith("image/"):
        meta["media_kind"] = "image"
        meta.update(_image_metadata(content))
    elif mime.startswith("video/"):
        meta["media_kind"] = "video"
        meta["format"] = mime.split("/")[-1] if "/" in mime else "video"
        ext = name.rsplit(".", 1)[-1] if "." in name else ""
        if ext:
            meta["extension"] = ext
    elif mime.startswith("audio/"):
        meta["media_kind"] = "audio"

    return meta


def _image_metadata(content: bytes) -> dict[str, Any]:
    try:
        from PIL import Image
        import io

        with Image.open(io.BytesIO(content)) as img:
            w, h = img.size
            return {
                "width": w,
                "height": h,
                "format": (img.format or "").lower(),
            }
    except Exception:
        return {}
