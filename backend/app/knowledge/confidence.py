"""Knowledge confidence propagation — uncertainty spread and semantic risk scoring.

Implements graph-based confidence decay across linked semantic triples and
heuristics for assessing reliability of extracted knowledge and AI answers.
Stdlib + dataclasses only; no external dependencies.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import replace

from app.knowledge.ontology import SemanticTriple

__all__ = ["ConfidencePropagator"]

DECAY_FACTOR = 0.85
MIN_CONFIDENCE = 0.1
HIGH_THRESHOLD = 0.8
MEDIUM_THRESHOLD = 0.5

_RISK_EXPLANATIONS: dict[str, str] = {
    "low": "Knowledge base is reliable",
    "medium": "Some facts require verification",
    "high": "Significant uncertainty detected",
    "critical": "Knowledge base is highly unreliable",
}


class ConfidencePropagator:
    """Propagate low confidence through entity-linked triples and score semantic risk."""

    DECAY_FACTOR = DECAY_FACTOR
    MIN_CONFIDENCE = MIN_CONFIDENCE
    HIGH_THRESHOLD = HIGH_THRESHOLD
    MEDIUM_THRESHOLD = MEDIUM_THRESHOLD

    def propagate(
        self,
        triples: list[SemanticTriple],
        depth: int = 3,
    ) -> list[SemanticTriple]:
        """Spread uncertainty from unreliable entities via BFS; return new triple instances."""
        if not triples:
            return []

        depth = max(0, depth)
        adjusted = [t.confidence for t in triples]

        entity_to_indices: dict[str, set[int]] = defaultdict(set)
        entity_neighbors: dict[str, set[str]] = defaultdict(set)

        for index, triple in enumerate(triples):
            entity_to_indices[triple.subject].add(index)
            entity_to_indices[triple.object_].add(index)
            entity_neighbors[triple.subject].add(triple.object_)
            entity_neighbors[triple.object_].add(triple.subject)

        unreliable_entities = [
            entity
            for entity, indices in entity_to_indices.items()
            if indices and all(triples[i].confidence < self.MEDIUM_THRESHOLD for i in indices)
        ]

        for seed in unreliable_entities:
            queue: deque[tuple[str, int]] = deque([(seed, 0)])
            best_hop: dict[str, int] = {seed: 0}

            while queue:
                entity, hop = queue.popleft()
                if hop > depth:
                    continue

                factor = self.DECAY_FACTOR**hop
                for index in entity_to_indices[entity]:
                    propagated = max(triples[index].confidence * factor, self.MIN_CONFIDENCE)
                    adjusted[index] = min(adjusted[index], propagated)

                if hop >= depth:
                    continue

                next_hop = hop + 1
                for neighbor in entity_neighbors[entity]:
                    if neighbor not in best_hop or next_hop < best_hop[neighbor]:
                        best_hop[neighbor] = next_hop
                        queue.append((neighbor, next_hop))

        return [
            replace(triple, confidence=adjusted[index])
            for index, triple in enumerate(triples)
        ]

    def get_risk_score(self, triples: list[SemanticTriple]) -> dict:
        """Compute a 0–100 semantic risk score and human-readable summary."""
        total = len(triples)
        if total == 0:
            return {
                "risk_score": 0,
                "risk_level": "low",
                "low_confidence_triples": 0,
                "disputed_triples": 0,
                "total_triples": 0,
                "explanation": _RISK_EXPLANATIONS["low"],
            }

        low_confidence_triples = sum(1 for t in triples if t.confidence < 0.5)
        disputed_triples = sum(
            1
            for t in triples
            if t.provenance is not None and t.provenance.validation_status == "disputed"
        )

        low_conf_ratio = low_confidence_triples / total
        disputed_ratio = disputed_triples / total
        risk_score = int((low_conf_ratio * 0.6 + disputed_ratio * 0.4) * 100)
        risk_score = max(0, min(100, risk_score))

        if risk_score <= 25:
            risk_level = "low"
        elif risk_score <= 50:
            risk_level = "medium"
        elif risk_score <= 75:
            risk_level = "high"
        else:
            risk_level = "critical"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "low_confidence_triples": low_confidence_triples,
            "disputed_triples": disputed_triples,
            "total_triples": total,
            "explanation": _RISK_EXPLANATIONS[risk_level],
        }

    def flag_risky_conclusions(
        self,
        triples: list[SemanticTriple],
        answer_text: str,
    ) -> dict:
        """Flag answer text that cites entities backed by low-confidence triples."""
        answer_lower = answer_text.lower()
        risky_entities: list[str] = []

        for triple in triples:
            if triple.confidence >= self.MEDIUM_THRESHOLD:
                continue
            for entity in (triple.subject, triple.object_):
                if entity.lower() in answer_lower and entity not in risky_entities:
                    risky_entities.append(entity)

        has_risky_claims = bool(risky_entities)
        risk_score = self.get_risk_score(triples)["risk_score"]

        warning = None
        if has_risky_claims:
            entities_preview = ", ".join(risky_entities[:5])
            if len(risky_entities) > 5:
                entities_preview += f" (+{len(risky_entities) - 5} more)"
            warning = (
                f"Answer references low-confidence entities: {entities_preview}. "
                "Verify before relying on this response."
            )

        return {
            "has_risky_claims": has_risky_claims,
            "risk_score": risk_score,
            "risky_entities": risky_entities,
            "warning": warning,
        }
