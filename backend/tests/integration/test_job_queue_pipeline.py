"""Integration tests for Redis ingestion job queue."""

from __future__ import annotations

import json

import pytest

from app.services.job_queue import (
    FAILED_KEY,
    PROCESSING_KEY,
    QUEUE_KEY,
    IngestionJobQueue,
)


@pytest.mark.integration
class TestJobQueuePipeline:
    async def test_enqueue_and_dequeue_fifo(self, patch_redis, fake_redis):
        queue = IngestionJobQueue()

        assert await queue.enqueue("doc-1", "user-1") is True
        assert await queue.enqueue("doc-2", "user-1") is True

        first = await queue.dequeue()
        second = await queue.dequeue()

        assert first is not None and first["doc_id"] == "doc-1"
        assert second is not None and second["doc_id"] == "doc-2"
        assert await fake_redis.llen(QUEUE_KEY) == 0
        assert await fake_redis.hlen(PROCESSING_KEY) == 2

    async def test_high_priority_dequeued_first(self, patch_redis):
        queue = IngestionJobQueue()

        await queue.enqueue("normal-doc", "user-1", priority=0)
        await queue.enqueue("urgent-doc", "user-1", priority=1)

        job = await queue.dequeue()
        assert job is not None
        assert job["doc_id"] == "urgent-doc"

    async def test_complete_removes_processing_entry(self, patch_redis, fake_redis):
        queue = IngestionJobQueue()
        await queue.enqueue("doc-complete", "user-1")
        await queue.dequeue()

        await queue.complete("doc-complete")
        assert await fake_redis.hlen(PROCESSING_KEY) == 0

    async def test_fail_moves_job_to_failed_set(self, patch_redis, fake_redis):
        queue = IngestionJobQueue()
        await queue.enqueue("doc-fail", "user-1")
        await queue.dequeue()

        await queue.fail("doc-fail", "parse error")

        assert await fake_redis.hlen(PROCESSING_KEY) == 0
        assert await fake_redis.hlen(FAILED_KEY) == 1
        failed_raw = await fake_redis.hget(FAILED_KEY, "doc-fail")
        assert failed_raw is not None
        failed = json.loads(failed_raw)
        assert failed["error"] == "parse error"

    async def test_retry_failed_requeues_job(self, patch_redis, fake_redis):
        queue = IngestionJobQueue()
        await queue.enqueue("doc-retry", "user-1")
        await queue.dequeue()
        await queue.fail("doc-retry", "temporary error")

        assert await queue.retry_failed("doc-retry") is True
        assert await fake_redis.hlen(FAILED_KEY) == 0
        assert await fake_redis.llen(QUEUE_KEY) == 1

    async def test_enqueue_returns_false_without_redis(self, monkeypatch):
        def _redis_unavailable():
            raise RuntimeError("redis unavailable")

        monkeypatch.setattr("app.services.job_queue.get_redis", _redis_unavailable)
        queue = IngestionJobQueue()
        assert await queue.enqueue("doc-offline", "user-1") is False

    async def test_queue_stats_reflect_pipeline_state(self, patch_redis):
        queue = IngestionJobQueue()
        await queue.enqueue("doc-a", "user-1")
        await queue.enqueue("doc-b", "user-1", priority=1)
        await queue.dequeue()

        stats = await queue.get_queue_stats()
        assert stats["available"] is True
        assert stats["queued"] == 1
        assert stats["queued_high"] == 0
        assert stats["processing"] == 1
