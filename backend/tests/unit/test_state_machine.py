"""Unit tests for document lifecycle state machine (no DB)."""

from app.core.state_machine import (
    DocumentEvent,
    DocumentState,
    DocumentStateMachine,
    InvalidTransitionError,
)


def _sm() -> DocumentStateMachine:
    return DocumentStateMachine()


def test_valid_transition_uploaded_to_validating():
    sm = _sm()
    assert sm.transition(DocumentState.UPLOADED, DocumentEvent.VALIDATE) == DocumentState.VALIDATING


def test_valid_transition_full_happy_path():
    sm = _sm()
    steps = [
        (DocumentState.UPLOADED, DocumentEvent.VALIDATE, DocumentState.VALIDATING),
        (DocumentState.VALIDATING, DocumentEvent.QUEUE, DocumentState.QUEUED),
        (DocumentState.QUEUED, DocumentEvent.START_PARSE, DocumentState.PARSING),
        (DocumentState.PARSING, DocumentEvent.FINISH_PARSE, DocumentState.CHUNKING),
        (DocumentState.CHUNKING, DocumentEvent.START_EMBED, DocumentState.EMBEDDING),
        (DocumentState.EMBEDDING, DocumentEvent.FINISH_EMBED, DocumentState.GRAPH_ENRICHMENT),
        (DocumentState.GRAPH_ENRICHMENT, DocumentEvent.FINISH_GRAPH, DocumentState.INDEXED),
        (DocumentState.INDEXED, DocumentEvent.COMPLETE, DocumentState.READY),
    ]
    state = DocumentState.UPLOADED
    for current, event, expected in steps:
        assert sm.transition(state, event) == expected
        state = expected
    assert state == DocumentState.READY


def test_invalid_transition_raises_error():
    sm = _sm()
    try:
        sm.transition(DocumentState.READY, DocumentEvent.VALIDATE)
        raise AssertionError("Expected InvalidTransitionError")
    except InvalidTransitionError:
        pass


def test_get_allowed_events():
    sm = _sm()
    assert set(sm.get_allowed_events(DocumentState.UPLOADED)) == {DocumentEvent.VALIDATE}
    assert set(sm.get_allowed_events(DocumentState.FAILED_PARSE)) == {DocumentEvent.RETRY}


def test_is_terminal():
    sm = _sm()
    assert sm.is_terminal(DocumentState.READY) is True
    assert sm.is_terminal(DocumentState.FAILED_VALIDATION) is True
    assert sm.is_terminal(DocumentState.PARSING) is False


def test_is_failed():
    sm = _sm()
    for failed in (
        DocumentState.FAILED_PARSE,
        DocumentState.FAILED_EMBEDDING,
        DocumentState.FAILED_GRAPH,
        DocumentState.FAILED_VALIDATION,
    ):
        assert sm.is_failed(failed) is True
    assert sm.is_failed(DocumentState.READY) is False
    assert sm.is_failed(DocumentState.INDEXED) is False


def test_can_retry():
    sm = _sm()
    assert sm.can_retry(DocumentState.FAILED_PARSE) is True
    assert sm.can_retry(DocumentState.FAILED_EMBEDDING) is True
    assert sm.can_retry(DocumentState.FAILED_GRAPH) is True
    assert sm.can_retry(DocumentState.READY) is False
    assert sm.can_retry(DocumentState.INDEXED) is False


def test_partial_success_path():
    sm = _sm()
    state = DocumentState.EMBEDDING
    state = sm.transition(state, DocumentEvent.FINISH_EMBED)
    assert state == DocumentState.GRAPH_ENRICHMENT
    state = sm.transition(state, DocumentEvent.FAIL_GRAPH)
    assert state == DocumentState.PARTIAL_SUCCESS
    state = sm.transition(state, DocumentEvent.COMPLETE)
    assert state == DocumentState.READY
