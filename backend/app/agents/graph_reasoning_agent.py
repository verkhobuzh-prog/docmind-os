"""Graph reasoning agent — contradictions, risks, and cross-document link detection."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import get_logger
from app.db.supabase import get_supabase, run_supabase
from app.knowledge.confidence import ConfidencePropagator
from app.knowledge.ontology import EntityType, ProvenanceRecord, RelationType, SemanticTriple
from app.services.provenance_service import ProvenanceService

logger = get_logger(__name__)

TRIPLES_TABLE = "semantic_triples"
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

__all__ = ["GraphReasoningAgent", "ReasoningFinding"]


@dataclass
class ReasoningFinding:
    finding_type: str  # contradiction | risk | hidden_relation | anomaly
    severity: str  # low | medium | high | critical
    title: str
    description: str
    entities_involved: list[str]
    doc_ids_involved: list[str]
    evidence: list[str]
    confidence: float
    recommendation: str


class GraphReasoningAgent:
    """Cognitive agent for semantic graph reasoning across user documents."""

    def __init__(self) -> None:
        self._provenance = ProvenanceService()
        self._propagator = ConfidencePropagator()

    async def analyze_document(
        self,
        doc_id: str,
        user_id: str,
    ) -> list[ReasoningFinding]:
        """Run all detectors for a single document and return sorted findings."""
        try:
            triples = await self._load_triples(doc_id, user_id)
            if not triples:
                return []

            findings: list[ReasoningFinding] = []
            findings.extend(await self._detect_temporal_conflicts(triples, user_id))
            findings.extend(self._detect_confidence_anomalies(triples))
            findings.extend(await self._detect_duplicate_relations(triples, user_id))

            findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))
            return findings
        except Exception as exc:
            logger.warning(
                "analyze_document failed for doc %s (user %s): %s",
                doc_id,
                user_id,
                exc,
            )
            return []

    async def _detect_temporal_conflicts(
        self,
        triples: list[dict],
        user_id: str,
    ) -> list[ReasoningFinding]:
        """Detect contradictory object assertions for the same subject and predicate."""
        findings: list[ReasoningFinding] = []
        try:
            keys: set[tuple[str, str]] = set()
            for row in triples:
                subject = str(row.get("subject", "")).strip()
                predicate = str(row.get("predicate", "")).strip()
                if subject and predicate:
                    keys.add((subject, predicate))

            seen_pairs: set[tuple[str, str, str, str]] = set()

            for subject, predicate in keys:
                related = await self._fetch_triples_by_subject_predicate(
                    user_id, subject, predicate
                )
                if len(related) < 2:
                    continue

                by_object: dict[str, list[dict]] = defaultdict(list)
                for row in related:
                    obj = str(row.get("object_") or row.get("object") or "").strip()
                    if obj:
                        by_object[obj.lower()].append(row)

                if len(by_object) < 2:
                    continue

                doc_sets = {
                    obj: {str(r.get("doc_id", "")) for r in rows}
                    for obj, rows in by_object.items()
                }
                objects = list(by_object.keys())
                for i, obj_a in enumerate(objects):
                    for obj_b in objects[i + 1 :]:
                        docs_a = doc_sets[obj_a]
                        docs_b = doc_sets[obj_b]
                        if docs_a == docs_b and len(docs_a) == 1:
                            continue
                        pair_key = tuple(sorted([obj_a, obj_b]) + sorted(docs_a | docs_b))
                        if pair_key in seen_pairs:
                            continue
                        seen_pairs.add(pair_key)

                        row_a = by_object[obj_a][0]
                        row_b = by_object[obj_b][0]
                        evidence_a = str(row_a.get("evidence_quote") or "").strip()
                        evidence_b = str(row_b.get("evidence_quote") or "").strip()
                        doc_ids = sorted(docs_a | docs_b)

                        findings.append(
                            ReasoningFinding(
                                finding_type="contradiction",
                                severity="high",
                                title=f"Contradiction: {subject} — {predicate}",
                                description=(
                                    f"Different objects asserted for ({subject}, {predicate}): "
                                    f"'{by_object[obj_a][0].get('object_') or obj_a}' vs "
                                    f"'{by_object[obj_b][0].get('object_') or obj_b}' "
                                    f"across {len(doc_ids)} document(s)."
                                ),
                                entities_involved=[subject],
                                doc_ids_involved=doc_ids,
                                evidence=[e for e in (evidence_a, evidence_b) if e],
                                confidence=min(
                                    float(row_a.get("confidence", 0.5)),
                                    float(row_b.get("confidence", 0.5)),
                                ),
                                recommendation=(
                                    "Review source documents and reconcile conflicting assertions "
                                    "or mark disputed triples for human verification."
                                ),
                            )
                        )
        except Exception as exc:
            logger.warning("Temporal conflict detection failed: %s", exc)
        return findings

    def _detect_confidence_anomalies(self, triples: list[dict]) -> list[ReasoningFinding]:
        """Flag low-confidence clusters and disputed facts in a triple set."""
        findings: list[ReasoningFinding] = []
        try:
            if not triples:
                return findings

            total = len(triples)
            low_conf = [
                t for t in triples if float(t.get("confidence", 1.0)) < 0.5
            ]
            disputed = [
                t
                for t in triples
                if str(t.get("validation_status") or "") == "disputed"
            ]

            low_ratio = len(low_conf) / total
            if low_ratio > 0.3:
                severity = "high" if low_ratio >= 0.6 else "medium"
                findings.append(
                    ReasoningFinding(
                        finding_type="anomaly",
                        severity=severity,
                        title="Low-confidence fact cluster",
                        description=(
                            f"{len(low_conf)} of {total} triples ({low_ratio:.0%}) "
                            "have confidence below 0.5."
                        ),
                        entities_involved=[],
                        doc_ids_involved=sorted(
                            {str(t.get("doc_id", "")) for t in low_conf if t.get("doc_id")}
                        ),
                        evidence=[
                            str(t.get("evidence_quote") or "")[:200]
                            for t in low_conf[:3]
                            if t.get("evidence_quote")
                        ],
                        confidence=1.0 - low_ratio,
                        recommendation=(
                            "Re-run extraction, add human verification, or exclude "
                            "low-confidence facts from automated decisions."
                        ),
                    )
                )

            if disputed:
                findings.append(
                    ReasoningFinding(
                        finding_type="risk",
                        severity="high" if len(disputed) / total >= 0.2 else "medium",
                        title="Disputed facts present",
                        description=(
                            f"{len(disputed)} disputed triple(s) found in this analysis scope."
                        ),
                        entities_involved=[],
                        doc_ids_involved=sorted(
                            {str(t.get("doc_id", "")) for t in disputed if t.get("doc_id")}
                        ),
                        evidence=[
                            str(t.get("evidence_quote") or "")[:200]
                            for t in disputed[:3]
                            if t.get("evidence_quote")
                        ],
                        confidence=0.9,
                        recommendation=(
                            "Resolve disputed triples before using this knowledge in "
                            "downstream RAG or compliance workflows."
                        ),
                    )
                )
        except Exception as exc:
            logger.warning("Confidence anomaly detection failed: %s", exc)
        return findings

    async def _detect_duplicate_relations(
        self,
        triples: list[dict],
        user_id: str,
    ) -> list[ReasoningFinding]:
        """Detect the same relation asserted across documents with divergent confidence."""
        findings: list[ReasoningFinding] = []
        try:
            keys: set[tuple[str, str, str]] = set()
            for row in triples:
                subject = str(row.get("subject", "")).strip()
                predicate = str(row.get("predicate", "")).strip()
                obj = str(row.get("object_") or row.get("object") or "").strip()
                if subject and predicate and obj:
                    keys.add((subject, predicate, obj))

            for subject, predicate, obj in keys:
                related = await self._fetch_triples_by_relation(
                    user_id, subject, predicate, obj
                )
                if len(related) < 2:
                    continue

                doc_conf: dict[str, float] = {}
                for row in related:
                    doc_id = str(row.get("doc_id", ""))
                    if doc_id:
                        doc_conf[doc_id] = float(row.get("confidence", 0.0))

                if len(doc_conf) < 2:
                    continue

                confidences = list(doc_conf.values())
                spread = max(confidences) - min(confidences)
                if spread <= 0.3:
                    continue

                findings.append(
                    ReasoningFinding(
                        finding_type="anomaly",
                        severity="medium",
                        title="Conflicting confidence for duplicate relation",
                        description=(
                            f"Relation ({subject})-[{predicate}]->({obj}) appears in "
                            f"{len(doc_conf)} documents with confidence spread {spread:.2f}."
                        ),
                        entities_involved=[subject, obj],
                        doc_ids_involved=sorted(doc_conf.keys()),
                        evidence=[
                            str(r.get("evidence_quote") or "")[:200]
                            for r in related[:3]
                            if r.get("evidence_quote")
                        ],
                        confidence=min(confidences),
                        recommendation=(
                            "Confirm whether documents reflect an update over time or "
                            "an extraction error; align confidence via human review."
                        ),
                    )
                )
        except Exception as exc:
            logger.warning("Duplicate relation detection failed: %s", exc)
        return findings

    async def compare_documents(
        self,
        doc_ids: list[str],
        user_id: str,
    ) -> dict:
        """Compare 2–5 documents for shared entities, contradictions, and aggregate risk."""
        empty = {
            "documents_analyzed": 0,
            "common_entities": [],
            "contradictions": [],
            "risk_score": 0,
            "summary": "No documents analyzed.",
        }
        try:
            unique_ids = list(dict.fromkeys(doc_ids))[:5]
            if len(unique_ids) < 2:
                return {
                    **empty,
                    "summary": "At least two document IDs are required for comparison.",
                }

            all_triples: list[dict] = []
            entity_docs: dict[str, set[str]] = defaultdict(set)

            for doc_id in unique_ids:
                rows = await self._load_triples(doc_id, user_id)
                all_triples.extend(rows)
                for row in rows:
                    doc = str(row.get("doc_id", doc_id))
                    for entity in (
                        str(row.get("subject", "")).strip(),
                        str(row.get("object_") or row.get("object") or "").strip(),
                    ):
                        if entity:
                            entity_docs[entity].add(doc)

            common_entities = sorted(
                entity for entity, docs in entity_docs.items() if len(docs) >= 2
            )

            contradictions = await self._detect_temporal_conflicts(all_triples, user_id)
            semantic = self._rows_to_semantic_triples(all_triples)
            risk = self._propagator.get_risk_score(semantic)

            contradiction_count = len(contradictions)
            summary = (
                f"Compared {len(unique_ids)} documents ({len(all_triples)} triples). "
                f"{len(common_entities)} shared entities, {contradiction_count} contradiction(s). "
                f"Risk score: {risk['risk_score']}/100 ({risk['risk_level']}). "
                f"{risk['explanation']}"
            )

            return {
                "documents_analyzed": len(unique_ids),
                "common_entities": common_entities,
                "contradictions": contradictions,
                "risk_score": risk["risk_score"],
                "summary": summary,
            }
        except Exception as exc:
            logger.warning(
                "compare_documents failed for user %s: %s",
                user_id,
                exc,
            )
            return empty

    async def _load_triples(self, doc_id: str, user_id: str) -> list[dict]:
        """Load semantic triple rows for a document via ProvenanceService."""
        try:
            return await self._provenance.get_triples_for_document(
                doc_id=doc_id,
                user_id=user_id,
                min_confidence=0.0,
            )
        except Exception as exc:
            logger.warning(
                "Failed to load triples for doc %s (user %s): %s",
                doc_id,
                user_id,
                exc,
            )
            return []

    async def _fetch_triples_by_subject_predicate(
        self,
        user_id: str,
        subject: str,
        predicate: str,
    ) -> list[dict]:
        """Fetch all user triples matching subject and predicate."""
        try:
            user_docs = set(await self._provenance._get_user_doc_ids(user_id))
            if not user_docs:
                return []

            client = get_supabase()

            def _query():
                return (
                    client.table(TRIPLES_TABLE)
                    .select(
                        "subject, predicate, object_, doc_id, confidence, "
                        "evidence_quote, validation_status"
                    )
                    .eq("subject", subject)
                    .eq("predicate", predicate)
                    .execute()
                )

            result = await run_supabase(_query)
            rows = result.data or []
            return [r for r in rows if str(r.get("doc_id", "")) in user_docs]
        except Exception as exc:
            logger.warning(
                "Failed to fetch triples for (%r, %r): %s",
                subject,
                predicate,
                exc,
            )
            return []

    async def _fetch_triples_by_relation(
        self,
        user_id: str,
        subject: str,
        predicate: str,
        object_: str,
    ) -> list[dict]:
        """Fetch all user triples matching a full relation key."""
        try:
            user_docs = set(await self._provenance._get_user_doc_ids(user_id))
            if not user_docs:
                return []

            client = get_supabase()

            def _query():
                return (
                    client.table(TRIPLES_TABLE)
                    .select(
                        "subject, predicate, object_, doc_id, confidence, "
                        "evidence_quote, validation_status"
                    )
                    .eq("subject", subject)
                    .eq("predicate", predicate)
                    .eq("object_", object_)
                    .execute()
                )

            result = await run_supabase(_query)
            rows = result.data or []
            return [r for r in rows if str(r.get("doc_id", "")) in user_docs]
        except Exception as exc:
            logger.warning(
                "Failed to fetch relation triples for %r: %s",
                subject,
                exc,
            )
            return []

    def _rows_to_semantic_triples(self, rows: list[dict]) -> list[SemanticTriple]:
        """Convert Postgres triple rows to SemanticTriple instances for risk scoring."""
        triples: list[SemanticTriple] = []
        for row in rows:
            try:
                validation_status = str(row.get("validation_status") or "auto-extracted")
                provenance = ProvenanceRecord(
                    doc_id=str(row.get("doc_id", "")),
                    chunk_id=str(row.get("chunk_id") or ""),
                    page_num=None,
                    extraction_model=str(row.get("extraction_model") or "unknown"),
                    extracted_at=datetime.now(timezone.utc),
                    confidence=float(row.get("confidence", 0.0)),
                    evidence_quote=str(row.get("evidence_quote") or ""),
                    validation_status=validation_status,
                )
                triples.append(
                    SemanticTriple(
                        subject=str(row.get("subject", "")),
                        subject_type=self._parse_entity_type(row.get("subject_type")),
                        predicate=self._parse_relation_type(row.get("predicate")),
                        object_=str(row.get("object_") or row.get("object") or ""),
                        object_type=self._parse_entity_type(row.get("object_type")),
                        confidence=float(row.get("confidence", 0.0)),
                        evidence_quote=str(row.get("evidence_quote") or ""),
                        provenance=provenance,
                    )
                )
            except Exception as exc:
                logger.warning("Skipping invalid triple row: %s", exc)
        return triples

    @staticmethod
    def _parse_entity_type(value: object | None) -> EntityType:
        try:
            return EntityType(str(value or ""))
        except ValueError:
            return EntityType.EVENT

    @staticmethod
    def _parse_relation_type(value: object | None) -> RelationType:
        try:
            return RelationType(str(value or ""))
        except ValueError:
            return RelationType.RELATED_TO
