# DocMind OS (DocumentOS)

> ## ✅ Phase 1 MVP — **COMPLETED**
> Backend API is production-ready for integration testing.  
> **Tests:** 9/9 passed | **Docs:** [Phase 1 Report](docs/PHASE1_COMPLETION.md)

Enterprise AI Document SaaS — upload, parse, search, and chat with business documents.

| | |
|---|---|
| **Phase** | 1 ✅ Complete → Phase 2 🚧 In Progress |
| **Repository** | https://github.com/verkhobuzh-prog/docmind-os |

---

## Phase 1 API — All Endpoints

| Status | Method | Endpoint | Auth | Description |
|--------|--------|----------|------|-------------|
| ✅ | `GET` | `/health` | — | Health check (Supabase, Redis) |
| ✅ | `GET` | `/api/v1/auth/me` | JWT | Current user profile |
| ✅ | `POST` | `/api/v1/documents/upload` | JWT | Upload file + auto-ingest |
| ✅ | `GET` | `/api/v1/documents` | JWT | List user documents |
| ✅ | `GET` | `/api/v1/documents/{id}` | JWT | Get document by ID |
| ✅ | `POST` | `/api/v1/documents/{id}/ingest` | JWT | Parse, chunk, embed |
| ✅ | `POST` | `/api/v1/chat` | JWT | RAG Q&A + citations (SSE) |

**Swagger UI:** http://localhost:8000/docs

### Example: Upload

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer $SUPABASE_JWT" \
  -F "file=@report.pdf"
```

### Example: Chat

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer $SUPABASE_JWT" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the key findings?", "top_k": 8}'
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | Python 3.12, FastAPI, Uvicorn |
| Auth / Storage | Supabase |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| AI | OpenAI (embeddings + GPT-4o-mini) |
| Parsing | PyMuPDF, pandas, tiktoken |

---

## Quick Start

```bash
git clone https://github.com/verkhobuzh-prog/docmind-os.git
cd docmind-os
cp .env.example .env
# Set: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY
docker compose up --build backend postgres redis
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

## Run Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

## Roadmap

| Phase | Status | Focus |
|-------|--------|-------|
| **Phase 1** | ✅ **Done** | Auth, upload, ingestion, RAG chat |
| **Phase 2** | 🚧 In Progress | Multi-tenant, frontend, Temporal, reranking |
| Phase 3 | Planned | Billing (Stripe), integrations, observability |
| Phase 4 | Planned | LLM router, conflict resolution, evaluation |

## Documentation

- [**Architectural Passport**](docs/ARCHITECTURAL_PASSPORT.md) — архітектурний паспорт
- [Developer Passport](docs/DEVELOPER_PASSPORT.md) — онбординг розробника
- [Phase 1 Completion Report](docs/PHASE1_COMPLETION.md)
- [Platform Architecture](docs/architecture/README.md)
- [CHANGELOG](CHANGELOG.md)

## License

Proprietary — All rights reserved.