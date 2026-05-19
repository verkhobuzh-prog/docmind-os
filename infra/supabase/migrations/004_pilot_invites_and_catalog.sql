-- DocMind OS — Personal pilot: invites, members, document catalog fields

-- ─── Invite codes ───────────────────────────────────────────────────────────
create table if not exists public.invite_codes (
    id uuid primary key default gen_random_uuid(),
    code text not null unique,
    label text,
    created_by uuid,
    max_uses int not null default 10 check (max_uses > 0),
    use_count int not null default 0 check (use_count >= 0),
    expires_at timestamptz,
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create index if not exists invite_codes_code_active_idx
    on public.invite_codes (code)
    where is_active = true;

-- ─── Pilot members (who joined via invite) ───────────────────────────────────
create table if not exists public.pilot_members (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique,
    email text not null,
    display_name text,
    invite_code_id uuid references public.invite_codes (id) on delete set null,
    invite_code text,
    joined_at timestamptz not null default now()
);

create index if not exists pilot_members_joined_idx
    on public.pilot_members (joined_at desc);

-- ─── Document catalog / dedup ────────────────────────────────────────────────
alter table public.documents
    add column if not exists content_hash text,
    add column if not exists subject text,
    add column if not exists document_type text;

create index if not exists documents_user_content_hash_idx
    on public.documents (user_id, content_hash)
    where deleted_at is null and content_hash is not null;

create index if not exists documents_user_subject_idx
    on public.documents (user_id, subject)
    where deleted_at is null;

comment on column public.documents.content_hash is 'SHA-256 hex of file bytes for duplicate detection';
comment on column public.documents.subject is 'Auto-detected subject (e.g. Алгебра, Фізика)';
comment on column public.documents.document_type is 'Auto-detected type: notes, homework, photo, video, etc.';
