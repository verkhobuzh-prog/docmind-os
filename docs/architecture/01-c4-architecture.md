# C4 Architecture — Doc-Hub

## Level 1: System Context

```mermaid
C4Context
    title System Context — Doc-Hub

    Person(user, "User", "Analyst, lawyer, ops team member")
    Person(admin, "Org Admin", "Manages workspace, billing, RBAC")
    System(dochub, "Doc-Hub", "AI Document Platform")
    System_Ext(supabase, "Supabase", "Auth, PostgreSQL, Storage, pgvector")
    System_Ext(llm, "LLM Providers", "OpenAI, Anthropic, Google, local vLLM")
    System_Ext(stripe, "Stripe", "Billing")
    System_Ext(storage, "Object Storage", "S3 / MinIO / Supabase Storage")
    System_Ext(integrations, "Integrations", "Google Drive, Notion, SharePoint")

    Rel(user, dochub, "Upload, search, chat with documents")
    Rel(admin, dochub, "Manage org, permissions, billing")
    Rel(dochub, supabase, "Auth, data, vectors")
    Rel(dochub, llm, "Embeddings, generation, rerank")
    Rel(dochub, stripe, "Subscriptions, usage billing")
    Rel(dochub, storage, "Raw files, parsed artifacts")
    Rel(dochub, integrations, "Sync external sources")
```

| Actor | Interaction |
|-------|-------------|
| **End User** | Upload docs, semantic search, RAG chat, view insights |
| **Org Admin** | RBAC, workspaces, quotas, audit, conflict resolution |
| **System Integrator** | REST API, webhooks, OAuth connectors |

---

## Level 2: Containers

```mermaid
C4Container
    title Containers — Doc-Hub

    Person(user, "User")

    Container_Boundary(dochub, "Doc-Hub Platform") {
        Container(web, "Web App", "React 19, TS, TanStack Query", "SPA + SSR shell")
        Container(api, "API Gateway", "FastAPI", "REST, auth, orchestration")
        Container(workers, "Workers", "Python + Temporal", "Ingestion, embeddings, indexing")
        Container(router, "LLM Router", "Python service", "Model selection, fallback")
        Container(redis, "Redis", "Redis 7", "Cache, rate limit, sessions")
        ContainerDb(pg, "PostgreSQL", "Supabase PG + pgvector", "Tenants, docs, vectors, audit")
        Container(blob, "Object Storage", "S3-compatible", "Original + parsed files")
    }

    System_Ext(llm, "LLM APIs")
    System_Ext(nats, "NATS JetStream", "Event bus (Phase 3+)")

    Rel(user, web, "HTTPS")
    Rel(web, api, "REST / SSE")
    Rel(api, pg, "SQL + RLS")
    Rel(api, redis, "Cache / limits")
    Rel(api, workers, "Temporal workflows")
    Rel(workers, blob, "Read/write artifacts")
    Rel(workers, pg, "Chunks, embeddings metadata")
    Rel(router, llm, "Inference")
    Rel(api, router, "Sync chat / analysis")
    Rel(workers, nats, "Publish events")
```

| Container | Responsibility | Phase |
|-----------|----------------|-------|
| **Web App** | UI, auth client, real-time status | 1 |
| **API Gateway** | AuthZ, CRUD, job triggers, chat API | 1 |
| **Workers** | Parse, chunk, embed, index | 1–2 |
| **LLM Router** | Model routing, cost caps, fallback | 4 |
| **Redis** | Rate limiting, job status cache | 1 |
| **PostgreSQL** | Source of truth + pgvector | 1 |
| **Object Storage** | Binary documents | 1 |
| **NATS/Kafka** | Domain events, decoupling | 3 |

---

## Level 3: API Component (Phase 1 focus)

```mermaid
flowchart TB
    subgraph API["FastAPI — app/"]
        MAIN[main.py<br/>lifespan, CORS, middleware]
        CFG[core/config.py]
        SEC[core/security.py]
        DB[(db/supabase.py)]
        REDIS[(db/redis.py)]
        AUTH[api/v1/auth]
        DOCS[api/v1/documents]
        INGEST[api/v1/ingest]
        SVC[services/]
    end

    MAIN --> CFG
    MAIN --> DB
    MAIN --> REDIS
    AUTH --> SEC
    AUTH --> DB
    DOCS --> SVC
    INGEST --> SVC
    SVC --> DB
```

---

## Deployment Views

| Environment | Topology |
|-------------|----------|
| **Dev** | Docker Compose: api + postgres + redis + minio |
| **Staging** | K8s single cluster, Supabase cloud, managed Redis |
| **Prod** | K8s multi-AZ, Supabase Pro, dedicated workers pool, CDN |
