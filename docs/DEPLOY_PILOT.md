# Deploy — Personal Pilot (Vercel + Render)

## 1. Supabase

1. Run migrations `001`–`005` in SQL Editor (in order):
   - `001_documents.sql`
   - `002_document_chunks.sql`
   - `003_knowledge_graph_metadata.sql`
   - `004_profiles.sql`
   - `005_pilot_invites_and_catalog.sql`
2. Storage bucket `documents` (private).
3. Auth: Email provider enabled.

## 2. Render (backend)

1. New **Web Service** → Docker, root `backend/`, Dockerfile `backend/Dockerfile`.
2. Or connect repo and use `render.yaml`.
3. **Critical:** set `DATABASE_URL` to Supabase **Postgres connection string** (Session mode), same DB where documents/chunks are written.
4. Environment:

| Variable | Example |
|----------|---------|
| `ENVIRONMENT` | `production` |
| `SUPABASE_URL` | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` |
| `OPENAI_API_KEY` | `sk-...` |
| `DATABASE_URL` | `postgresql://postgres.[ref]:[pwd]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` |
| `FRONTEND_URL` | `https://your-app.vercel.app` |
| `PILOT_ADMIN_EMAILS` | `you@gmail.com` |
| `PILOT_INVITE_REQUIRED` | `true` |

Health: `GET https://your-api.onrender.com/health`

## 3. Vercel (frontend)

Root directory: `frontend`

| Variable | Value |
|----------|--------|
| `VITE_SUPABASE_URL` | same as Supabase |
| `VITE_SUPABASE_ANON_KEY` | anon key |
| `VITE_API_URL` | `https://your-api.onrender.com` |

## 4. First admin flow

1. Register your admin email in Supabase.
2. Open app → **Адмін** → create invite `DM-...`.
3. Share link: `https://your-app.vercel.app/?invite=DM-XXXX`.

## 5. Features in this pilot

- Invite-only registration (configurable).
- Auto **subject** + **document_type** on upload.
- **Duplicate** files marked in UI (not deleted).
- **Photos/videos**: stored + catalogued; RAG ingest skipped for media.
