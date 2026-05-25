# Observability & Cost — Doc-Hub

## OpenTelemetry stack

```
FastAPI → OTel SDK → Collector → Tempo (traces) + Prometheus (metrics) + Loki (logs)
                                                      ↓
                                                 Grafana dashboards
```

### Instrumentation points

| Span name | Attributes |
|-----------|------------|
| `http.request` | method, route, status, org_id |
| `db.query` | table, duration_ms |
| `ai.embed` | model, tokens, cost_usd |
| `ai.generate` | model, prompt_tokens, completion_tokens, latency_ms |
| `rag.retrieve` | query_hash, chunks_count, rerank_score |
| `workflow.ingest` | document_id, stage |

---

## AI logging schema

```sql
create table ai_request_logs (
  id uuid primary key,
  org_id uuid not null,
  user_id uuid,
  request_type text,  -- embed | chat | summarize
  model text,
  prompt_hash text,   -- never store raw PII prompts in prod
  prompt_tokens int,
  completion_tokens int,
  latency_ms int,
  cost_usd numeric(10,6),
  faithfulness_score float,
  citation_accuracy float,
  status text,
  error_code text,
  trace_id text,
  created_at timestamptz default now()
);
```

---

## Cost tracking

| Granularity | Storage | Alert |
|-------------|---------|-------|
| Per request | `ai_request_logs` | — |
| Per user/day | materialized view | 80% quota email |
| Per org/month | `org_usage_monthly` | Stripe metered + Slack |

```python
# Cost formula
cost = (prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000
```

Dashboards:
- **Grafana**: p50/p95 latency, error rate, cost/hour by model
- **Supabase**: SQL views for org admins (their data only via RLS)

---

## Alerting

| Alert | Threshold | Channel |
|-------|-----------|---------|
| API error rate | > 1% 5min | PagerDuty |
| LLM latency p95 | > 10s | Slack |
| Org cost | > 90% cap | Email + webhook |
| Ingestion backlog | > 1000 jobs | Slack |
| Faithfulness drop | < 0.7 avg 1h | Engineering |
