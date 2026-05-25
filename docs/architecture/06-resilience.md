# Resilience Strategy — Doc-Hub

## Multi-layer defense

```
Client retry → API rate limit → Circuit breaker → Fallback model → Safe Mode → Human escalation
```

---

## Circuit breaker (per dependency)

| Dependency | Failure threshold | Open duration | Fallback |
|------------|-------------------|---------------|----------|
| OpenAI | 5 failures / 30s | 60s | Claude Haiku |
| Claude | 5 / 30s | 60s | GPT-4o-mini |
| Supabase DB | 3 / 10s | 30s | Read replica / cache |
| Redis | 3 / 10s | 15s | In-memory LRU (degraded) |
| Parser service | 3 / 60s | 120s | Queue + notify user |

Implementation: `tenacity` + custom breaker in `app/core/resilience.py` (Phase 2).

---

## Retry policy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((httpx.TimeoutException, RateLimitError)),
)
async def embed_chunks(chunks: list[str]) -> list[list[float]]:
    ...
```

---

## Workflow snapshots (Temporal)

- **IngestWorkflow**: checkpoint after parse, after chunk, after embed
- On failure: resume from last checkpoint (idempotent upsert on `document_chunks`)
- **Rollback**: soft-delete chunks + set `documents.status = failed` + retain raw in storage

---

## Failure isolation per org

- Separate rate-limit buckets: `ratelimit:{org_id}:{endpoint}`
- Worker fair-queue: max concurrent ingest per org = `plan.ingest_concurrency`
- Cost cap: hard stop embeddings when `org.monthly_ai_spend >= cap`

---

## Health degradation levels

| Level | Condition | Behavior |
|-------|-----------|----------|
| L0 Healthy | All green | Full features |
| L1 Degraded | Redis down | No cache, slower |
| L2 Limited | LLM primary down | Fallback chain |
| L3 Safe Mode | Multi-service failure | Read-only + queue |
| L4 Maintenance | Manual | 503 + status page |
