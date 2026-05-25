"""Integration tests linking ingestion pipeline stages to lifecycle states."""

from __future__ import annotations

import pytest

from app.core.state_machine import DocumentEvent, DocumentState, DocumentStateMachine

INGESTION_PIPELINE_EVENTS: list[tuple[DocumentEvent, DocumentState]] = [
    (DocumentEvent.VALIDATE, DocumentState.VALIDATING),
    (DocumentEvent.QUEUE, DocumentState.QUEUED),
    (DocumentEvent.START_PARSE, DocumentState.PARSING),
    (DocumentEvent.FINISH_PARSE, DocumentState.CHUNKING),
    (DocumentEvent.START_EMBED, DocumentState.EMBEDDING),
    (DocumentEvent.FINISH_EMBED, DocumentState.GRAPH_ENRICHMENT),
    (DocumentEvent.FINISH_GRAPH, DocumentState.INDEXED),
    (DocumentEvent.COMPLETE, DocumentState.READY),
]


@pytest.mark.integration
class TestLifecyclePipeline:
    def test_ingestion_events_follow_valid_state_path(self):
        sm = DocumentStateMachine()
        state = DocumentState.UPLOADED

        for event, expected in INGESTION_PIPELINE_EVENTS:
            state = sm.transition(state, event)
            assert state == expected

        assert sm.is_terminal(state)

    def test_parse_failure_allows_retry_back_to_queue(self):
        sm = DocumentStateMachine()
        state = sm.transition(DocumentState.UPLOADED, DocumentEvent.VALIDATE)
        state = sm.transition(state, DocumentEvent.QUEUE)
        state = sm.transition(state, DocumentEvent.START_PARSE)
        state = sm.transition(state, DocumentEvent.FAIL_PARSE)

        assert sm.is_failed(state)
        assert sm.can_retry(state)
        state = sm.transition(state, DocumentEvent.RETRY)
        assert state == DocumentState.RETRYING
        state = sm.transition(state, DocumentEvent.QUEUE)
        assert state == DocumentState.QUEUED

    def test_graph_failure_can_finish_as_partial_success(self):
        sm = DocumentStateMachine()
        state = DocumentState.EMBEDDING
        state = sm.transition(state, DocumentEvent.FINISH_EMBED)
        state = sm.transition(state, DocumentEvent.FAIL_GRAPH)
        assert state == DocumentState.PARTIAL_SUCCESS
        state = sm.transition(state, DocumentEvent.COMPLETE)
        assert state == DocumentState.READY
