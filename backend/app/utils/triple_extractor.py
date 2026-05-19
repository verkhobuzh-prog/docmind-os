"""LLM-driven extraction of semantic triples from document chunks."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone

from openai import OpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.knowledge.ontology import (
    EntityType,
    ProvenanceRecord,
    RelationType,
    SemanticTriple,
)

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are an expert knowledge graph extractor.
Extract semantic triples from the text.
Return ONLY valid JSON array, no markdown, no explanation.
Each triple: {"subject": str, "subject_type": str, "predicate": str,
              "object": str, "object_type": str,
              "confidence": float 0-1, "evidence_quote": str (max 200 chars)}
Valid subject_type/object_type: PERSON, ORGANIZATION, AGREEMENT, ASSET,
LOCATION, LEGAL_CASE, FINANCIAL_RECORD, EVENT, POLICY, PROJECT
Valid predicate: SIGNED_BY, REFERENCES, SUPERSEDES, CANCELLED_BY, PART_OF,
OWNS, RELATED_TO, APPROVED_BY, TERMINATED_BY, ASSOCIATED_WITH
Extract only facts clearly stated in text. If unsure, set confidence < 0.5."""


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _parse_entity_type(value: str) -> EntityType | None:
    try:
        return EntityType(value.strip().upper())
    except ValueError:
        return None


def _parse_relation_type(value: str) -> RelationType | None:
    try:
        return RelationType(value.strip().upper())
    except ValueError:
        return None


class TripleExtractor:
    """Extract ontology-aligned semantic triples from chunk text via OpenAI."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model or settings.TRIPLE_EXTRACTION_MODEL

    async def extract(
        self,
        chunk_text: str,
        doc_id: str,
        chunk_id: str,
        page_num: int | None = None,
    ) -> list[SemanticTriple]:
        if not settings.TRIPLE_EXTRACTION_ENABLED:
            return []

        if not chunk_text.strip():
            return []

        if not settings.openai_configured:
            logger.warning("OPENAI_API_KEY not set — skipping triple extraction")
            return []

        try:
            raw = await self._call_llm(chunk_text)
            items = self._parse_response(raw)
            return self._build_triples(
                items,
                doc_id=doc_id,
                chunk_id=chunk_id,
                page_num=page_num,
            )
        except Exception as exc:
            logger.warning(
                "Triple extraction failed for doc=%s chunk=%s: %s",
                doc_id,
                chunk_id,
                exc,
            )
            return []

    async def _call_llm(self, chunk_text: str) -> str:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        def _create() -> str:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": chunk_text},
                ],
                temperature=0.0,
            )
            return response.choices[0].message.content or "[]"

        return await asyncio.to_thread(_create)

    def _parse_response(self, raw: str) -> list[dict]:
        text = _strip_json_fence(raw)
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            for key in ("triples", "results", "data"):
                candidate = parsed.get(key)
                if isinstance(candidate, list):
                    return [item for item in candidate if isinstance(item, dict)]
        return []

    def _build_triples(
        self,
        items: list[dict],
        *,
        doc_id: str,
        chunk_id: str,
        page_num: int | None,
    ) -> list[SemanticTriple]:
        threshold = settings.CONFIDENCE_THRESHOLD
        extracted_at = datetime.now(timezone.utc)
        triples: list[SemanticTriple] = []

        for item in items:
            try:
                confidence = float(item.get("confidence", 0))
            except (TypeError, ValueError):
                continue

            if confidence < threshold:
                continue

            subject_type = _parse_entity_type(str(item.get("subject_type", "")))
            object_type = _parse_entity_type(str(item.get("object_type", "")))
            predicate = _parse_relation_type(str(item.get("predicate", "")))
            if subject_type is None or object_type is None or predicate is None:
                continue

            subject = str(item.get("subject", "")).strip()
            object_ = str(item.get("object", "")).strip()
            if not subject or not object_:
                continue

            evidence_quote = str(item.get("evidence_quote", "")).strip()[:200]

            provenance = ProvenanceRecord(
                doc_id=doc_id,
                chunk_id=chunk_id,
                page_num=page_num,
                extraction_model=self._model,
                extracted_at=extracted_at,
                confidence=confidence,
                evidence_quote=evidence_quote,
            )

            triples.append(
                SemanticTriple(
                    subject=subject,
                    subject_type=subject_type,
                    predicate=predicate,
                    object_=object_,
                    object_type=object_type,
                    confidence=confidence,
                    evidence_quote=evidence_quote,
                    provenance=provenance,
                )
            )

        return triples
