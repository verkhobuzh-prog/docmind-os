# DocMind OS — Architecture (Phase 1)

## Layers

- **Frontend** — React SPA, Supabase Auth client, REST calls to FastAPI
- **API** — FastAPI, JWT validation via Supabase, business logic in services
- **Data** — Supabase PostgreSQL + RLS, Storage (Phase 2+)

## Backend modules

| Module | Responsibility |
|--------|----------------|
| `core` | Settings, Supabase client, JWT security |
| `api/v1/auth` | Current user profile |
| `api/v1/documents` | Document CRUD |
| `services` | Supabase data access |
