# Development Roadmap — Doc-Hub

## Phase 1 — MVP (Q2 2026)

**Goal:** Auth + Upload + Parse + Embeddings + Basic RAG

| Module | Deliverables | DoD |
|--------|--------------|-----|
| Auth | Supabase JWT, `/auth/me` | RLS tested |
| Documents | CRUD, storage upload | E2E upload |
| Ingestion | Temporal workflow stub, Unstructured parse | PDF indexed |
| Embeddings | OpenAI/Voyage batch → pgvector | Search returns chunks |
| RAG Chat | `/chat` SSE, citations | Faithfulness > 0.7 test set |
| Infra | Docker Compose, migrations | CI green |

**Code structure (backend):**
```
backend/app/
├── main.py
├── core/{config,security,logging,resilience}
├── db/{supabase,redis}
├── api/v1/{auth,documents,ingest,chat}
├── services/{document,ingestion,embedding,rag}
├── agents/          # Phase 2+
└── workflows/       # Temporal definitions
```

---

## Phase 2 — Multi-tenant (Q3 2026)

- Organizations, Workspaces, RBAC matrix
- Strict RLS on all tables
- Hybrid search (vector + BM25)
- Cohere rerank
- Cost tracking per org
- Redis rate limiting

---

## Phase 3 — Enterprise (Q4 2026)

- Stripe billing + usage meters
- Integrations (Drive, Notion)
- Full audit trail
- OpenTelemetry + Grafana
- NATS event bus
- SSO/SAML

---

## Phase 4 — Production Grade (2027)

- Conflict Resolver Agent + UI
- LLM Router Agent
- Evaluation pipeline (LLM-as-Judge)
- Safe Mode + circuit breakers
- Data governance + GDPR tooling
- K8s + ArgoCD production

---

## Multi-Agent map (Phase 4)

| Agent | Triggers | Outputs |
|-------|----------|---------|
| Ingestion | DocumentUploaded | ChunksCreated |
| Retrieval | QueryReceived | RetrievedContext |
| Generation | ContextReady | Answer + citations |
| LLM Router | Any AI call | ModelDecision |
| Security | Pre/post generation | Allow/Block/Redact |
| Billing | Token usage | QuotaUpdated |
| Observability | All events | Metrics + alerts |
| Conflict Resolver | ConflictDetected | Resolution |
