from pathlib import Path

README = """# DocMind OS (DocumentOS)

Enterprise AI Document SaaS - upload, parse, search, and chat with citations.

| Phase | Status |
|-------|--------|
| Phase 1 | Complete - FastAPI backend, RAG, Docker |
| Phase 2 | Complete - React frontend (Vite + Tailwind) |
| Repository | https://github.com/verkhobuzh-prog/docmind-os |

## Quick Start

```bash
git clone https://github.com/verkhobuzh-prog/docmind-os.git
cd docmind-os
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Frontend (dev) | http://localhost:5173 |

Frontend local dev:

```bash
cd frontend && cp .env.example .env && npm install && npm run dev
```

## Phase 2 Frontend

- Auth (Supabase login/register)
- Dashboard (upload, list, re-index, document selection)
- Chat (RAG + citations, scoped to selected documents)
- Settings (Trust Level guardrails)

## Docs

- [Architectural Passport](docs/ARCHITECTURAL_PASSPORT.md)
- [Developer Passport](docs/DEVELOPER_PASSPORT.md)
- [Phase 1 Completion](docs/PHASE1_COMPLETION.md)
"""

Path(__file__).resolve().parents[1].joinpath("README.md").write_text(README, encoding="utf-8")
print("wrote README.md")
