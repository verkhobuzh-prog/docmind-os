# DocMind OS — Platform Architecture

## Phase 1 Status: ✅ **COMPLETED** (May 2026)

Implemented: Auth, Document Upload, Ingestion (parse/chunk/embed), RAG Chat, hybrid search, Docker stack, **9/9 pytest**.  
**Phase 2:** Multi-tenant, frontend, Temporal — in progress.

| Document | Description |
|----------|-------------|
| [../ARCHITECTURAL_PASSPORT.md](../ARCHITECTURAL_PASSPORT.md) | Архітектурний паспорт проекту |
| [../DEVELOPER_PASSPORT.md](../DEVELOPER_PASSPORT.md) | **Паспорт розробника** |
| [../PHASE1_COMPLETION.md](../PHASE1_COMPLETION.md) | Phase 1 completion report |

| Doc | Topic |
|-----|-------|
| [01-c4-architecture.md](./01-c4-architecture.md) | Context → Container → Component |
| [02-ai-pipeline.md](./02-ai-pipeline.md) | Ingestion, RAG 2.0, LLM Router |
| [03-data-model.md](./03-data-model.md) | ERD, tables, RLS |
| [04-rbac-permissions.md](./04-rbac-permissions.md) | Roles, permissions matrix, ABAC |
| [05-conflict-management.md](./05-conflict-management.md) | Optimistic locking, Safe Mode |
| [06-resilience.md](./06-resilience.md) | Circuit breaker, retry, isolation |
| [07-observability-cost.md](./07-observability-cost.md) | OTel, AI logs, cost tracking |
| [08-kubernetes-topology.md](./08-kubernetes-topology.md) | K8s, Helm, GitOps |
| [09-roadmap.md](./09-roadmap.md) | Phase 1–4 roadmap |
