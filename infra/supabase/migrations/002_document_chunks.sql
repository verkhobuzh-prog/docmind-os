-- DocMind OS — Phase 1.5: organizations, workspaces, chunks, AI logs
-- documents table is defined in 001_documents.sql

create extension if not exists vector;

-- ─── Organizations (Phase 2 ready) ─────────────────────────────────────────
create table if not exists public.organizations (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    slug text not null unique,
    plan text not null default 'free',
    settings jsonb not null default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ─── Workspaces ─────────────────────────────────────────────────────────────
create table if not exists public.workspaces (
    id uuid primary key default uuid_generate_v4(),
    org_id uuid references public.organizations(id) on delete cascade,
    name text not null,
    settings jsonb not null default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Link documents.org_id → organizations (if column exists from 001)
do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'public' and table_name = 'documents' and column_name = 'org_id'
    ) then
        alter table public.documents
            drop constraint if exists documents_org_id_fkey;
        alter table public.documents
            add constraint documents_org_id_fkey
            foreign key (org_id) references public.organizations(id) on delete set null;
    end if;
exception
    when others then null;
end $$;

-- ─── Document chunks (ingestion / embeddings) ────────────────────────────────
-- Columns: id, document_id, chunk_index, content, metadata, embedding, created_at
create table if not exists public.document_chunks (
    id uuid primary key default uuid_generate_v4(),
    document_id uuid not null references public.documents(id) on delete cascade,
    chunk_index int not null check (chunk_index >= 0),
    content text not null check (char_length(content) > 0),
    metadata jsonb not null default '{}',
    embedding vector(1536),
    content_tsv tsvector generated always as (to_tsvector('english', coalesce(content, ''))) stored,
    created_at timestamptz not null default now(),
    unique (document_id, chunk_index)
);

comment on table public.document_chunks is 'Parsed text chunks with optional pgvector embeddings';
comment on column public.document_chunks.embedding is 'OpenAI text-embedding-3-large (1536 dims)';

create index if not exists document_chunks_doc_idx
    on public.document_chunks (document_id, chunk_index);
create index if not exists document_chunks_fts_idx
    on public.document_chunks using gin (content_tsv);

-- HNSW index for vector search (enable after first embeddings ingested)
-- create index if not exists document_chunks_embedding_hnsw_idx
--     on public.document_chunks using hnsw (embedding vector_cosine_ops);

-- ─── AI request logs ─────────────────────────────────────────────────────────
create table if not exists public.ai_request_logs (
    id uuid primary key default uuid_generate_v4(),
    org_id uuid,
    user_id uuid,
    request_type text not null,
    model text,
    prompt_tokens int default 0,
    completion_tokens int default 0,
    latency_ms int,
    cost_usd numeric(10, 6) default 0,
    faithfulness_score float,
    status text not null default 'ok',
    trace_id text,
    created_at timestamptz not null default now()
);

-- ─── RLS for chunks ──────────────────────────────────────────────────────────
alter table public.document_chunks enable row level security;

drop policy if exists "chunks_select_via_document" on public.document_chunks;
create policy "chunks_select_via_document"
    on public.document_chunks for select
    using (
        exists (
            select 1 from public.documents d
            where d.id = document_chunks.document_id
              and d.user_id = auth.uid()
              and d.deleted_at is null
        )
    );
