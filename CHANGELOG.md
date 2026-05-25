# Changelog

All notable changes to Doc-Hub are documented in this file.

## [0.1.0] - 2026-05-17 — Phase 1 MVP ✅

### Added

- **FastAPI backend** with lifespan, CORS, JSON logging, request ID middleware
- **Authentication** via Supabase JWT (`/api/v1/auth/me`)
- **Document upload** to Supabase Storage (`POST /api/v1/documents/upload`)
- **Document CRUD** — list and get by ID
- **Ingestion pipeline** — parse (PDF, TXT, MD, Excel), chunk, embed, index
- **RAG chat** — hybrid search, GPT-4o-mini, citations, SSE streaming
- **Infrastructure** — Docker Compose (backend, postgres+pgvector, redis)
- **Database migrations** — `documents`, `document_chunks` tables + RLS
- **Tests** — pytest suite (9 tests, all passing)
- **Documentation** — README, architecture docs, Phase 1 completion report

### Security

- JWT validation on all protected endpoints
- Chat guardrails for prompt injection
- User-scoped data access (RLS-equivalent filtering)

### Known Limitations

See [docs/PHASE1_COMPLETION.md](docs/PHASE1_COMPLETION.md).

## [0.2.0] - 2026-05-17 — Phase 2 Frontend

### Added

- React + Vite + Tailwind frontend with Supabase auth
- Dashboard (upload, document list, selection for scoped chat)
- Chat UI with citation display
- Settings page with Trust Level guardrails
- Docker Compose frontend service (dev)
- Production Dockerfile (`frontend/Dockerfile.prod`) + nginx

---

## [Unreleased] — Phase 3

- Multi-tenant organizations and workspaces
- Temporal workflows
- Advanced reranking and hybrid search
