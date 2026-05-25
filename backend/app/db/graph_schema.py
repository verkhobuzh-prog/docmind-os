"""
DocMind OS — Legal Knowledge Graph Schema
FalkorDB / OpenCypher compatible

Nodes:   Person, Organization, Agreement, LegalCase, Policy
Edges:   SIGNED_BY, SUPERSEDES, REFERENCES, TERMINATED_BY
Temporal: кожне ребро має valid_from / valid_to

Usage:
    from app.db.graph_schema import LegalGraphSchema
    from app.db.graph import get_graph

    graph = get_graph("docmind_knowledge")
    schema = LegalGraphSchema(graph)
    await schema.initialize()
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from falkordb.graph import Graph

from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class NodeLabel(str, Enum):
    PERSON = "Person"
    ORGANIZATION = "Organization"
    AGREEMENT = "Agreement"
    LEGAL_CASE = "LegalCase"
    POLICY = "Policy"


class EdgeType(str, Enum):
    SIGNED_BY = "SIGNED_BY"
    SUPERSEDES = "SUPERSEDES"
    REFERENCES = "REFERENCES"
    TERMINATED_BY = "TERMINATED_BY"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────
# NODE DATACLASSES
# ─────────────────────────────────────────────

@dataclass
class PersonNode:
    """
    Фізична особа — підписант, сторона справи, автор документа.

    Properties:
        id          — унікальний ідентифікатор (UUID або зовнішній ID)
        full_name   — повне ім'я
        role        — роль у системі (lawyer, judge, signatory, etc.)
        org_id      — прив'язка до організації-власника знань
        source_doc  — документ, з якого вилучено сутність
        confidence  — впевненість вилучення (0.0–1.0)
        created_at  — час додавання у граф
    """

    id: str
    full_name: str
    role: Optional[str] = None
    org_id: Optional[str] = None
    source_doc: Optional[str] = None
    confidence: float = 1.0
    created_at: str = field(default_factory=_utc_now_iso)

    LABEL = NodeLabel.PERSON

    def to_cypher_props(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "role": self.role,
            "org_id": self.org_id,
            "source_doc": self.source_doc,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class OrganizationNode:
    """
    Юридична особа — компанія, орган влади, НГО.

    Properties:
        id           — UUID
        name         — офіційна назва
        legal_form   — ТОВ, АТ, ФОП, державний орган, etc.
        country      — ISO 3166-1 alpha-2
        reg_number   — реєстраційний номер (ЄДРПОУ, etc.)
        org_id       — tenant isolation
        confidence   — впевненість вилучення
    """

    id: str
    name: str
    legal_form: Optional[str] = None
    country: Optional[str] = None
    reg_number: Optional[str] = None
    org_id: Optional[str] = None
    confidence: float = 1.0
    created_at: str = field(default_factory=_utc_now_iso)

    LABEL = NodeLabel.ORGANIZATION

    def to_cypher_props(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "legal_form": self.legal_form,
            "country": self.country,
            "reg_number": self.reg_number,
            "org_id": self.org_id,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class AgreementNode:
    """
    Договір / угода / контракт.

    Properties:
        id              — UUID
        title           — назва договору
        agreement_type  — NDA, SLA, Employment, Procurement, etc.
        status          — draft | active | expired | terminated | superseded
        effective_date  — дата набрання чинності (ISO date string)
        expiry_date     — дата закінчення дії
        value_amount    — сума договору (якщо є)
        currency        — ISO 4217
        org_id          — tenant isolation
        doc_id          — UUID документа в DocMind (зв'язок з pgvector)
        confidence      — впевненість вилучення
    """

    id: str
    title: str
    agreement_type: Optional[str] = None
    status: str = "active"
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    value_amount: Optional[float] = None
    currency: Optional[str] = None
    org_id: Optional[str] = None
    doc_id: Optional[str] = None
    confidence: float = 1.0
    created_at: str = field(default_factory=_utc_now_iso)

    LABEL = NodeLabel.AGREEMENT

    def to_cypher_props(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "agreement_type": self.agreement_type,
            "status": self.status,
            "effective_date": self.effective_date,
            "expiry_date": self.expiry_date,
            "value_amount": self.value_amount,
            "currency": self.currency,
            "org_id": self.org_id,
            "doc_id": self.doc_id,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class LegalCaseNode:
    """
    Судова справа / юридичне провадження.

    Properties:
        id           — UUID
        case_number  — номер справи
        title        — назва/опис справи
        court        — назва суду
        status       — open | closed | appealed | settled
        filed_date   — дата подачі
        closed_date  — дата закриття
        jurisdiction — юрисдикція (країна/регіон)
        org_id       — tenant isolation
        doc_id       — UUID документа в DocMind
    """

    id: str
    case_number: str
    title: Optional[str] = None
    court: Optional[str] = None
    status: str = "open"
    filed_date: Optional[str] = None
    closed_date: Optional[str] = None
    jurisdiction: Optional[str] = None
    org_id: Optional[str] = None
    doc_id: Optional[str] = None
    confidence: float = 1.0
    created_at: str = field(default_factory=_utc_now_iso)

    LABEL = NodeLabel.LEGAL_CASE

    def to_cypher_props(self) -> dict:
        return {
            "id": self.id,
            "case_number": self.case_number,
            "title": self.title,
            "court": self.court,
            "status": self.status,
            "filed_date": self.filed_date,
            "closed_date": self.closed_date,
            "jurisdiction": self.jurisdiction,
            "org_id": self.org_id,
            "doc_id": self.doc_id,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class PolicyNode:
    """
    Внутрішня або зовнішня політика / регламент / норматив.

    Properties:
        id              — UUID
        title           — назва
        policy_type     — internal | regulatory | legal | compliance
        version         — версія (напр. "2.1.0")
        status          — draft | active | deprecated | superseded
        effective_date  — дата введення
        review_date     — дата наступного перегляду
        issuing_body    — хто випустив (організація або орган влади)
        org_id          — tenant isolation
        doc_id          — UUID документа в DocMind
    """

    id: str
    title: str
    policy_type: Optional[str] = None
    version: Optional[str] = None
    status: str = "active"
    effective_date: Optional[str] = None
    review_date: Optional[str] = None
    issuing_body: Optional[str] = None
    org_id: Optional[str] = None
    doc_id: Optional[str] = None
    confidence: float = 1.0
    created_at: str = field(default_factory=_utc_now_iso)

    LABEL = NodeLabel.POLICY

    def to_cypher_props(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "policy_type": self.policy_type,
            "version": self.version,
            "status": self.status,
            "effective_date": self.effective_date,
            "review_date": self.review_date,
            "issuing_body": self.issuing_body,
            "org_id": self.org_id,
            "doc_id": self.doc_id,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


# ─────────────────────────────────────────────
# TEMPORAL EDGE BASE
# ─────────────────────────────────────────────

@dataclass
class TemporalEdge:
    """
    Базовий клас для всіх temporal edges у legal graph.

    Temporal model:
        valid_from  — початок дії зв'язку (бізнес-час)
        valid_to    — кінець дії зв'язку (None = досі діє)
        extracted_at — коли LLM вилучив цей факт з документа
        source_doc  — UUID документа-джерела
        chunk_id    — UUID chunk-джерела (для provenance)
        confidence  — впевненість вилучення (0.0–1.0)
        model_id    — яка LLM модель вилучила факт
        evidence    — цитата-доказ з документа
    """

    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    extracted_at: str = field(default_factory=_utc_now_iso)
    source_doc: Optional[str] = None
    chunk_id: Optional[str] = None
    confidence: float = 1.0
    model_id: Optional[str] = None
    evidence: Optional[str] = None

    def temporal_props(self) -> dict:
        return {
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "extracted_at": self.extracted_at,
            "source_doc": self.source_doc,
            "chunk_id": self.chunk_id,
            "confidence": self.confidence,
            "model_id": self.model_id,
            "evidence": self.evidence,
        }


# ─────────────────────────────────────────────
# CONCRETE EDGES
# ─────────────────────────────────────────────

@dataclass
class SignedByEdge(TemporalEdge):
    """
    (Agreement)-[:SIGNED_BY]->(Person | Organization)

    Кожна сторона підписання — окреме ребро.

    Extra props:
        signatory_role  — роль при підписанні (директор, уповноважений, etc.)
        signature_type  — physical | electronic | digital
    """

    signatory_role: Optional[str] = None
    signature_type: str = "physical"

    EDGE_TYPE = EdgeType.SIGNED_BY

    def to_cypher_props(self) -> dict:
        return {
            **self.temporal_props(),
            "signatory_role": self.signatory_role,
            "signature_type": self.signature_type,
        }


@dataclass
class SupersedesEdge(TemporalEdge):
    """
    (Agreement | Policy)-[:SUPERSEDES]->(Agreement | Policy)

    Нова версія документа замінює стару.

    Extra props:
        reason          — причина заміни
        change_summary  — короткий опис змін
    """

    reason: Optional[str] = None
    change_summary: Optional[str] = None

    EDGE_TYPE = EdgeType.SUPERSEDES

    def to_cypher_props(self) -> dict:
        return {
            **self.temporal_props(),
            "reason": self.reason,
            "change_summary": self.change_summary,
        }


@dataclass
class ReferencesEdge(TemporalEdge):
    """
    (Agreement | Policy | LegalCase)-[:REFERENCES]->
    (Agreement | Policy | LegalCase | Organization | Person)

    Один документ посилається на інший.

    Extra props:
        reference_type  — тип посилання: cite | incorporate | amend | annex
        section         — розділ, де є посилання
    """

    reference_type: str = "cite"
    section: Optional[str] = None

    EDGE_TYPE = EdgeType.REFERENCES

    def to_cypher_props(self) -> dict:
        return {
            **self.temporal_props(),
            "reference_type": self.reference_type,
            "section": self.section,
        }


@dataclass
class TerminatedByEdge(TemporalEdge):
    """
    (Agreement | LegalCase)-[:TERMINATED_BY]->(Organization | Person | LegalCase)

    Хто або що припинило дію документа / справи.

    Extra props:
        termination_reason  — причина припинення
        termination_type    — expired | cancelled | court_order | mutual | breach
    """

    termination_reason: Optional[str] = None
    termination_type: str = "expired"

    EDGE_TYPE = EdgeType.TERMINATED_BY

    def to_cypher_props(self) -> dict:
        return {
            **self.temporal_props(),
            "termination_reason": self.termination_reason,
            "termination_type": self.termination_type,
        }


# ─────────────────────────────────────────────
# SCHEMA INITIALIZER
# ─────────────────────────────────────────────

class LegalGraphSchema:
    """
    Ініціалізація індексів у FalkorDB.

    Виклик при старті сервісу (idempotent — повторний виклик безпечний).

    Usage:
        from app.db.graph_schema import LegalGraphSchema
        from app.db.graph import get_graph

        graph = get_graph(settings.GRAPH_DB_NAME)
        if graph is not None:
            schema = LegalGraphSchema(graph)
            await schema.initialize()
    """

    NODE_INDEXES = [
        ("Person", "id"),
        ("Person", "org_id"),
        ("Person", "full_name"),
        ("Organization", "id"),
        ("Organization", "org_id"),
        ("Organization", "reg_number"),
        ("Agreement", "id"),
        ("Agreement", "org_id"),
        ("Agreement", "status"),
        ("Agreement", "doc_id"),
        ("LegalCase", "id"),
        ("LegalCase", "org_id"),
        ("LegalCase", "case_number"),
        ("LegalCase", "status"),
        ("Policy", "id"),
        ("Policy", "org_id"),
        ("Policy", "status"),
        ("Policy", "doc_id"),
    ]

    EDGE_INDEXES = [
        ("SIGNED_BY", "valid_from"),
        ("SIGNED_BY", "valid_to"),
        ("SUPERSEDES", "valid_from"),
        ("REFERENCES", "valid_from"),
        ("TERMINATED_BY", "valid_from"),
        ("TERMINATED_BY", "valid_to"),
    ]

    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    async def initialize(self) -> None:
        """Створити всі індекси. Idempotent."""
        logger.info("Initializing Legal Graph Schema...")

        for label, prop in self.NODE_INDEXES:
            await self._create_node_index(label, prop)

        for edge_type, prop in self.EDGE_INDEXES:
            await self._create_edge_index(edge_type, prop)

        logger.info("Legal Graph Schema initialized successfully.")

    async def _create_node_index(self, label: str, prop: str) -> None:
        query = f"CREATE INDEX FOR (n:{label}) ON (n.{prop})"
        try:
            await asyncio.to_thread(self.graph.query, query)
            logger.debug("Index created: %s.%s", label, prop)
        except Exception as exc:
            if "already indexed" not in str(exc).lower():
                logger.warning("Index %s.%s: %s", label, prop, exc)

    async def _create_edge_index(self, edge_type: str, prop: str) -> None:
        query = f"CREATE INDEX FOR ()-[r:{edge_type}]-() ON (r.{prop})"
        try:
            await asyncio.to_thread(self.graph.query, query)
            logger.debug("Edge index created: %s.%s", edge_type, prop)
        except Exception as exc:
            if "already indexed" not in str(exc).lower():
                logger.warning("Edge index %s.%s: %s", edge_type, prop, exc)

    async def drop_all(self) -> None:
        """⚠️ НЕБЕЗПЕЧНО: видалити весь граф. Тільки для тестів."""
        await asyncio.to_thread(self.graph.query, "MATCH (n) DETACH DELETE n")
        logger.warning("All graph nodes deleted!")


# ─────────────────────────────────────────────
# CYPHER QUERY HELPERS (Temporal-aware)
# ─────────────────────────────────────────────

class LegalGraphQueries:
    """
    Готові Cypher-запити для юридичного домену.

    Всі запити temporal-aware:
    - фільтрують за valid_from / valid_to
    - підтримують org_id isolation
    """

    @staticmethod
    def get_active_agreements_for_org(org_id: str, as_of_date: str) -> tuple[str, dict]:
        query = """
        MATCH (a:Agreement)
        WHERE a.org_id = $org_id
          AND a.status = 'active'
          AND (a.effective_date IS NULL OR a.effective_date <= $as_of_date)
          AND (a.expiry_date IS NULL OR a.expiry_date >= $as_of_date)
        RETURN a
        ORDER BY a.effective_date DESC
        """
        return query, {"org_id": org_id, "as_of_date": as_of_date}

    @staticmethod
    def get_signatories_at_date(
        agreement_id: str,
        as_of_date: str,
        org_id: str,
    ) -> tuple[str, dict]:
        query = """
        MATCH (a:Agreement {id: $agreement_id, org_id: $org_id})
              -[r:SIGNED_BY]->
              (s)
        WHERE (r.valid_from IS NULL OR r.valid_from <= $as_of_date)
          AND (r.valid_to   IS NULL OR r.valid_to   >= $as_of_date)
        RETURN s, r.signatory_role AS role, r.signature_type AS sig_type,
               r.valid_from AS signed_from, r.evidence AS evidence
        """
        return query, {
            "agreement_id": agreement_id,
            "as_of_date": as_of_date,
            "org_id": org_id,
        }

    @staticmethod
    def get_supersession_chain(
        document_id: str,
        doc_label: str,
        org_id: str,
    ) -> tuple[str, dict]:
        query = f"""
        MATCH path = (root:{doc_label} {{id: $document_id, org_id: $org_id}})
                     -[:SUPERSEDES*1..10]->
                     (current:{doc_label})
        WHERE NOT (current)-[:SUPERSEDES]->()
        RETURN nodes(path) AS chain,
               relationships(path) AS supersession_edges
        ORDER BY length(path) DESC
        LIMIT 1
        """
        return query, {"document_id": document_id, "org_id": org_id}

    @staticmethod
    def get_references_graph(
        document_id: str,
        org_id: str,
        max_depth: int = 3,
    ) -> tuple[str, dict]:
        safe_depth = min(max(1, max_depth), 5)
        query = f"""
        MATCH (start {{id: $document_id, org_id: $org_id}})
        CALL {{
            WITH start
            MATCH (start)-[r:REFERENCES*1..{safe_depth}]->(referenced)
            RETURN referenced AS node, r AS rels, 'outgoing' AS direction
            UNION
            WITH start
            MATCH (referencing)-[r:REFERENCES*1..{safe_depth}]->(start)
            RETURN referencing AS node, r AS rels, 'incoming' AS direction
        }}
        RETURN node, rels, direction
        """
        return query, {"document_id": document_id, "org_id": org_id}

    @staticmethod
    def find_terminated_agreements(
        org_id: str,
        terminated_after: str,
    ) -> tuple[str, dict]:
        query = """
        MATCH (a:Agreement {org_id: $org_id})
              -[r:TERMINATED_BY]->
              (terminator)
        WHERE r.valid_from >= $terminated_after
        RETURN a, terminator,
               r.termination_type   AS type,
               r.termination_reason AS reason,
               r.valid_from         AS terminated_at,
               r.evidence           AS evidence
        ORDER BY r.valid_from DESC
        """
        return query, {"org_id": org_id, "terminated_after": terminated_after}

    @staticmethod
    def get_org_legal_timeline(
        org_id: str,
        from_date: str,
        to_date: str,
    ) -> tuple[str, dict]:
        query = """
        MATCH (a:Agreement {org_id: $org_id})
        WHERE (a.effective_date >= $from_date AND a.effective_date <= $to_date)
           OR (a.expiry_date    >= $from_date AND a.expiry_date    <= $to_date)
        OPTIONAL MATCH (a)-[r:TERMINATED_BY]->(t)
        RETURN 'Agreement' AS entity_type,
               a.id        AS entity_id,
               a.title     AS title,
               a.status    AS status,
               a.effective_date AS event_date,
               r.termination_type AS termination_type
        UNION
        MATCH (p:Policy {org_id: $org_id})
        WHERE (p.effective_date >= $from_date AND p.effective_date <= $to_date)
        RETURN 'Policy'    AS entity_type,
               p.id        AS entity_id,
               p.title     AS title,
               p.status    AS status,
               p.effective_date AS event_date,
               NULL        AS termination_type
        ORDER BY event_date ASC
        """
        return query, {
            "org_id": org_id,
            "from_date": from_date,
            "to_date": to_date,
        }
