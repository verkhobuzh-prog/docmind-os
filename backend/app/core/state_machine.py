"""
Document lifecycle state machine for Doc-Hub ingestion pipeline.

Defines allowed states, events, and valid transitions for document processing
from upload through indexing (or failure / retry paths).
"""

from __future__ import annotations

from enum import Enum


class InvalidTransitionError(Exception):
    """Raised when an event is not valid for the current document state."""


class DocumentState(str, Enum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    QUEUED = "queued"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    GRAPH_ENRICHMENT = "graph_enrichment"
    INDEXED = "indexed"
    READY = "ready"
    FAILED_PARSE = "failed_parse"
    FAILED_EMBEDDING = "failed_embedding"
    FAILED_GRAPH = "failed_graph"
    FAILED_VALIDATION = "failed_validation"
    RETRYING = "retrying"
    PARTIAL_SUCCESS = "partial_success"


class DocumentEvent(str, Enum):
    VALIDATE = "validate"
    QUEUE = "queue"
    START_PARSE = "start_parse"
    FINISH_PARSE = "finish_parse"
    FAIL_PARSE = "fail_parse"
    START_CHUNK = "start_chunk"
    FINISH_CHUNK = "finish_chunk"
    START_EMBED = "start_embed"
    FINISH_EMBED = "finish_embed"
    FAIL_EMBED = "fail_embed"
    START_GRAPH = "start_graph"
    FINISH_GRAPH = "finish_graph"
    FAIL_GRAPH = "fail_graph"
    COMPLETE = "complete"
    RETRY = "retry"
    RESET = "reset"


TRANSITIONS: dict[tuple[DocumentState, DocumentEvent], DocumentState] = {
    (DocumentState.UPLOADED, DocumentEvent.VALIDATE): DocumentState.VALIDATING,
    (DocumentState.VALIDATING, DocumentEvent.QUEUE): DocumentState.QUEUED,
    (DocumentState.VALIDATING, DocumentEvent.FAIL_PARSE): DocumentState.FAILED_VALIDATION,
    (DocumentState.QUEUED, DocumentEvent.START_PARSE): DocumentState.PARSING,
    (DocumentState.PARSING, DocumentEvent.FINISH_PARSE): DocumentState.CHUNKING,
    (DocumentState.PARSING, DocumentEvent.FAIL_PARSE): DocumentState.FAILED_PARSE,
    (DocumentState.CHUNKING, DocumentEvent.START_EMBED): DocumentState.EMBEDDING,
    (DocumentState.EMBEDDING, DocumentEvent.FINISH_EMBED): DocumentState.GRAPH_ENRICHMENT,
    (DocumentState.EMBEDDING, DocumentEvent.FAIL_EMBED): DocumentState.FAILED_EMBEDDING,
    (DocumentState.GRAPH_ENRICHMENT, DocumentEvent.FINISH_GRAPH): DocumentState.INDEXED,
    (DocumentState.GRAPH_ENRICHMENT, DocumentEvent.FAIL_GRAPH): DocumentState.PARTIAL_SUCCESS,
    (DocumentState.INDEXED, DocumentEvent.COMPLETE): DocumentState.READY,
    (DocumentState.FAILED_PARSE, DocumentEvent.RETRY): DocumentState.RETRYING,
    (DocumentState.FAILED_EMBEDDING, DocumentEvent.RETRY): DocumentState.RETRYING,
    (DocumentState.FAILED_GRAPH, DocumentEvent.RETRY): DocumentState.RETRYING,
    (DocumentState.RETRYING, DocumentEvent.QUEUE): DocumentState.QUEUED,
    (DocumentState.PARTIAL_SUCCESS, DocumentEvent.COMPLETE): DocumentState.READY,
}

_TERMINAL_STATES = frozenset({DocumentState.READY, DocumentState.FAILED_VALIDATION})
_FAILED_STATES = frozenset(
    {
        DocumentState.FAILED_PARSE,
        DocumentState.FAILED_EMBEDDING,
        DocumentState.FAILED_GRAPH,
        DocumentState.FAILED_VALIDATION,
    }
)
_RETRYABLE_STATES = frozenset(
    {
        DocumentState.FAILED_PARSE,
        DocumentState.FAILED_EMBEDDING,
        DocumentState.FAILED_GRAPH,
    }
)


class DocumentStateMachine:
    """Finite state machine for document ingestion lifecycle."""

    def transition(
        self,
        current_state: DocumentState,
        event: DocumentEvent,
    ) -> DocumentState:
        key = (current_state, event)
        if key not in TRANSITIONS:
            raise InvalidTransitionError(f"Cannot {event} from {current_state}")
        return TRANSITIONS[key]

    def get_allowed_events(self, state: DocumentState) -> list[DocumentEvent]:
        return [event for (from_state, event) in TRANSITIONS if from_state == state]

    def is_terminal(self, state: DocumentState) -> bool:
        return state in _TERMINAL_STATES

    def is_failed(self, state: DocumentState) -> bool:
        return state in _FAILED_STATES

    def can_retry(self, state: DocumentState) -> bool:
        return state in _RETRYABLE_STATES


__all__ = [
    "DocumentState",
    "DocumentEvent",
    "TRANSITIONS",
    "DocumentStateMachine",
    "InvalidTransitionError",
]
