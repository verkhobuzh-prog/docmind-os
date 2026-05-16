"""Document parsers for the ingestion pipeline (Phase 1 MVP)."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedDocument:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    parser: str = "unknown"


def parse_document(content: bytes, mime_type: str, filename: str = "") -> ParsedDocument:
    """
    Parse raw file bytes into plain text.

    Supports: PDF (PyMuPDF), TXT, Markdown, Excel (pandas).
    """
    mime = (mime_type or "").lower()
    name = (filename or "").lower()

    if mime == "application/pdf" or name.endswith(".pdf"):
        return _parse_pdf(content)
    if mime in ("text/plain",) or name.endswith(".txt"):
        return _parse_text(content, parser="plaintext")
    if mime in ("text/markdown",) or name.endswith((".md", ".markdown")):
        return _parse_text(content, parser="markdown")
    if (
        mime
        in (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        )
        or name.endswith((".xlsx", ".xls"))
    ):
        return _parse_excel(content, filename)

    try:
        return _parse_text(content, parser="utf8_fallback")
    except Exception as exc:
        raise ValueError(f"Unsupported document type: {mime_type or filename}") from exc


def _parse_pdf(content: bytes) -> ParsedDocument:
    import fitz  # PyMuPDF

    pages: list[str] = []
    with fitz.open(stream=content, filetype="pdf") as doc:
        for page in doc:
            pages.append(page.get_text("text"))

    text = "\n\n".join(p.strip() for p in pages if p.strip())
    return ParsedDocument(
        text=text,
        metadata={"page_count": len(pages), "format": "pdf"},
        parser="pymupdf",
    )


def _parse_text(content: bytes, parser: str = "plaintext") -> ParsedDocument:
    text = content.decode("utf-8", errors="replace").strip()
    return ParsedDocument(text=text, metadata={"format": parser}, parser=parser)


def _parse_excel(content: bytes, filename: str) -> ParsedDocument:
    import pandas as pd

    buffer = io.BytesIO(content)
    sheets = pd.read_excel(buffer, sheet_name=None, engine="openpyxl")

    parts: list[str] = []
    sheet_names: list[str] = []
    for sheet_name, df in sheets.items():
        sheet_names.append(str(sheet_name))
        parts.append(f"## Sheet: {sheet_name}\n{df.to_string(index=False)}")

    text = "\n\n".join(parts).strip()
    return ParsedDocument(
        text=text,
        metadata={"sheet_count": len(sheets), "sheets": sheet_names, "format": "excel"},
        parser="pandas",
    )
