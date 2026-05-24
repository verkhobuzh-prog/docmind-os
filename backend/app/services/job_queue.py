"""Redis-based FIFO job queue for document ingestion."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.db.redis import get_redis

logger = get_logger(__name__)

QUEUE_KEY = "docmind:ingestion:queue"
PROCESSING_KEY = "docmind:ingestion:processing"
FAILED_KEY = "docmind:ingestion:failed"


def _redis_client():
    """Return Redis client or None if unavailable."""
    try:
        return get_redis()
    except RuntimeError:
        return None


class IngestionJobQueue:
    """
    Redis-based FIFO queue for ingestion jobs.
    Graceful fallback when Redis is unavailable.
    """

    async def enqueue(
        self,
        doc_id: str,
        user_id: str,
        priority: int = 0,
        metadata: dict | None = None,
    ) -> bool:
        """
        Add a job to the queue.

        priority: 0=normal, 1=high (high priority uses a separate list)
        Returns True on success, False if Redis is unavailable.
        """
        redis = _redis_client()
        if redis is None:
            logger.warning("Redis unavailable — job not queued: %s", doc_id)
            return False

        job = {
            "doc_id": doc_id,
            "user_id": user_id,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "priority": priority,
            "metadata": metadata or {},
        }

        try:
            queue = f"{QUEUE_KEY}:high" if priority > 0 else QUEUE_KEY
            await redis.rpush(queue, json.dumps(job))
            logger.info("Job enqueued: doc=%s priority=%d", doc_id, priority)
            return True
        except Exception as exc:
            logger.warning("Failed to enqueue job %s: %s", doc_id, exc)
            return False

    async def dequeue(self) -> dict[str, Any] | None:
        """
        Take the next job (high priority first).
        Returns None if the queue is empty or Redis is unavailable.
        """
        redis = _redis_client()
        if redis is None:
            return None

        try:
            raw = await redis.lpop(f"{QUEUE_KEY}:high")
            if raw is None:
                raw = await redis.lpop(QUEUE_KEY)
            if raw is None:
                return None

            job = json.loads(raw)
            await redis.hset(
                PROCESSING_KEY,
                job["doc_id"],
                json.dumps({**job, "started_at": datetime.now(timezone.utc).isoformat()}),
            )
            return job
        except Exception as exc:
            logger.warning("Dequeue error: %s", exc)
            return None

    async def complete(self, doc_id: str) -> None:
        """Remove job from processing after success."""
        redis = _redis_client()
        if redis is None:
            return
        try:
            await redis.hdel(PROCESSING_KEY, doc_id)
        except Exception as exc:
            logger.warning("Complete job error %s: %s", doc_id, exc)

    async def fail(self, doc_id: str, error: str) -> None:
        """Move job to the failed set."""
        redis = _redis_client()
        if redis is None:
            return
        try:
            job_raw = await redis.hget(PROCESSING_KEY, doc_id)
            if job_raw:
                job = json.loads(job_raw)
                job["failed_at"] = datetime.now(timezone.utc).isoformat()
                job["error"] = error
                await redis.hset(FAILED_KEY, doc_id, json.dumps(job))
                await redis.hdel(PROCESSING_KEY, doc_id)
        except Exception as exc:
            logger.warning("Fail job error %s: %s", doc_id, exc)

    async def get_queue_stats(self) -> dict[str, Any]:
        """Queue statistics."""
        redis = _redis_client()
        if redis is None:
            return {"available": False}
        try:
            queued = await redis.llen(QUEUE_KEY)
            queued_high = await redis.llen(f"{QUEUE_KEY}:high")
            processing = await redis.hlen(PROCESSING_KEY)
            failed = await redis.hlen(FAILED_KEY)
            return {
                "available": True,
                "queued": queued,
                "queued_high": queued_high,
                "processing": processing,
                "failed": failed,
                "total_pending": queued + queued_high,
            }
        except Exception as exc:
            logger.warning("Stats error: %s", exc)
            return {"available": False}

    async def retry_failed(self, doc_id: str) -> bool:
        """Move a failed job back into the queue."""
        redis = _redis_client()
        if redis is None:
            return False
        try:
            job_raw = await redis.hget(FAILED_KEY, doc_id)
            if not job_raw:
                return False
            job = json.loads(job_raw)
            job.pop("failed_at", None)
            job.pop("error", None)
            job["retried_at"] = datetime.now(timezone.utc).isoformat()
            await redis.rpush(QUEUE_KEY, json.dumps(job))
            await redis.hdel(FAILED_KEY, doc_id)
            return True
        except Exception as exc:
            logger.warning("Retry failed job %s: %s", doc_id, exc)
            return False


_queue: IngestionJobQueue | None = None


def get_job_queue() -> IngestionJobQueue:
    global _queue
    if _queue is None:
        _queue = IngestionJobQueue()
    return _queue
