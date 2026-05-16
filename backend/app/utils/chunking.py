"""Text chunking for RAG ingestion."""

from __future__ import annotations

import tiktoken

from app.core.config import settings


def chunk_text(
  text: str,
  *,
  chunk_size: int | None = None,
  overlap: int | None = None,
  model: str = "cl100k_base",
) -> list[str]:
  """
  Split text into overlapping token-based chunks.
  """
  if not text or not text.strip():
    return []

  enc = tiktoken.get_encoding(model)
  size = chunk_size or settings.INGESTION_CHUNK_SIZE
  ov = overlap or settings.INGESTION_CHUNK_OVERLAP

  tokens = enc.encode(text)
  if len(tokens) <= size:
    return [text.strip()]

  chunks: list[str] = []
  start = 0
  while start < len(tokens):
    end = min(start + size, len(tokens))
    chunk_tokens = tokens[start:end]
    chunks.append(enc.decode(chunk_tokens).strip())
    if end >= len(tokens):
      break
    start = end - ov

  return [c for c in chunks if c]
