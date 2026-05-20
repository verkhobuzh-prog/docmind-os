# DocMind OS — Architecture

> **Повний архітектурний паспорт:** [ARCHITECTURAL_PASSPORT.md](./ARCHITECTURAL_PASSPORT.md)

## Quick Links

| Document | Topic |
|----------|-------|
| [ARCHITECTURAL_PASSPORT.md](./ARCHITECTURAL_PASSPORT.md) | Архітектурний паспорт проекту |
| [DEVELOPER_PASSPORT.md](./DEVELOPER_PASSPORT.md) | **Паспорт розробника (онбординг)** |
| [PHASE1_COMPLETION.md](./PHASE1_COMPLETION.md) | Phase 1 checklist |
| [architecture/](./architecture/README.md) | C4, AI pipeline, data model, roadmap |

## Phase 1 Layers (implemented)

- **API** — FastAPI, JWT via Supabase, services layer
- **Data** — PostgreSQL + pgvector, Supabase Storage, Redis
- **AI** — OpenAI embeddings + GPT-4o-mini RAG

## Backend modules

| Module | Responsibility |
|--------|----------------|
| `core` | Config, security, logging, exceptions |
| `db` | Supabase, PostgreSQL pool, Redis |
| `api/v1` | auth, documents, ingestion, chat |
| `services` | Business logic |
| `utils` | Parsers, chunking, retrieval, guardrails |
