-- Doc-Hub — Phase 1: documents table + storage metadata + RLS
-- Run on Supabase (production) or local Postgres (dev via Docker)

create extension if not exists "uuid-ossp";

-- ─── Documents ───────────────────────────────────────────────────────────────
create table if not exists public.documents (
    id uuid primary key default uuid_generate_v4(),
    org_id uuid,
    user_id uuid not null,
    filename text not null check (char_length(filename) between 1 and 1024),
    title text not null check (char_length(title) between 1 and 500),
    storage_path text not null,
    mime_type text,
    size_bytes bigint not null default 0 check (size_bytes >= 0),
    status text not null default 'uploaded'
        check (status in ('uploaded', 'parsing', 'indexed', 'failed')),
    metadata jsonb not null default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    deleted_at timestamptz
);

-- Supabase: link user_id to auth.users when auth schema exists
do $$
begin
    if exists (select 1 from information_schema.schemata where schema_name = 'auth') then
        alter table public.documents
            drop constraint if exists documents_user_id_fkey;
        alter table public.documents
            add constraint documents_user_id_fkey
            foreign key (user_id) references auth.users(id) on delete cascade;
    end if;
exception
    when others then null;
end $$;

create index if not exists documents_user_id_idx
    on public.documents (user_id)
    where deleted_at is null;

create index if not exists documents_org_id_idx
    on public.documents (org_id)
    where deleted_at is null;

create index if not exists documents_status_idx
    on public.documents (status)
    where deleted_at is null;

-- ─── Row Level Security ──────────────────────────────────────────────────────
alter table public.documents enable row level security;

drop policy if exists "documents_select_own" on public.documents;
create policy "documents_select_own"
    on public.documents for select
    using (auth.uid() = user_id and deleted_at is null);

drop policy if exists "documents_insert_own" on public.documents;
create policy "documents_insert_own"
    on public.documents for insert
    with check (auth.uid() = user_id);

drop policy if exists "documents_update_own" on public.documents;
create policy "documents_update_own"
    on public.documents for update
    using (auth.uid() = user_id and deleted_at is null);

drop policy if exists "documents_delete_own" on public.documents;
create policy "documents_delete_own"
    on public.documents for delete
    using (auth.uid() = user_id);

-- ─── updated_at trigger ──────────────────────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists documents_updated_at on public.documents;
create trigger documents_updated_at
    before update on public.documents
    for each row execute function public.set_updated_at();

-- ─── Storage bucket (Supabase Dashboard / CLI) ───────────────────────────────
-- Create bucket named "documents" (public: false) in Supabase Storage.
-- Policy: authenticated users can upload/read their own paths:
--   {user_id}/{document_id}/{filename}
