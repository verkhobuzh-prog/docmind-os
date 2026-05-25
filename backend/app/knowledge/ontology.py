"""Doc-Hub V12.5 base ontology — entity types, relations, triples, and provenance.

Defines the canonical vocabulary for knowledge extraction, graph storage, and
audit trails. All types are stdlib-only (dataclasses + enums) so they can be
shared across ingestion, FalkorDB persistence, and API layers without extra deps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

__all__ = [
    "EntityType",
    "RelationType",
    "SemanticTriple",
    "ProvenanceRecord",
]


class EntityType(str, Enum):
    """Node labels in the Doc-Hub knowledge graph."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    AGREEMENT = "AGREEMENT"
    ASSET = "ASSET"
    LOCATION = "LOCATION"
    LEGAL_CASE = "LEGAL_CASE"
    FINANCIAL_RECORD = "FINANCIAL_RECORD"
    EVENT = "EVENT"
    POLICY = "POLICY"
    PROJECT = "PROJECT"


class RelationType(str, Enum):
    """Edge types between entities in the Doc-Hub knowledge graph."""

    SIGNED_BY = "SIGNED_BY"
    REFERENCES = "REFERENCES"
    SUPERSEDES = "SUPERSEDES"
    CANCELLED_BY = "CANCELLED_BY"
    PART_OF = "PART_OF"
    OWNS = "OWNS"
    RELATED_TO = "RELATED_TO"
    APPROVED_BY = "APPROVED_BY"
    TERMINATED_BY = "TERMINATED_BY"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"


@dataclass(frozen=True, slots=True)
class SemanticTriple:
    """A subject–predicate–object assertion extracted from document text."""

    subject: str
    subject_type: EntityType
    predicate: RelationType
    object_: str
    object_type: EntityType
    confidence: float  # 0.0–1.0
    evidence_quote: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    provenance: ProvenanceRecord | None = None


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    """Source attribution and validation state for an extracted fact or triple."""

    doc_id: str
    chunk_id: str
    page_num: int | None
    extraction_model: str
    extracted_at: datetime
    confidence: float
    evidence_quote: str
    validation_status: str = "auto-extracted"
