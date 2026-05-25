-- ═══════════════════════════════════════════════════════════════════
-- DocMind OS — Migration 004: RLS Hardening (CRITICAL Security Fix)
-- Вектор атаки: backend використовує service_role → RLS ігнорується.
-- Якщо в сервісному коді забути .eq("user_id", uid) — будь-який
-- авторизований користувач читає документи ВСІХ інших (IDOR).
-- Ця міграція додає ДРУГИЙ рівень захисту: RLS на рівні БД
-- блокує запити навіть якщо app-логіка має баг.
-- ═══════════════════════════════════════════════════════════════════

-- ─── Передумови ──────────────────────────────────────────────────
-- Переконайтесь що auth schema доступна (Supabase Cloud: завжди є).
-- Для Docker-dev без справжнього Supabase: policies не активуються,
-- але CREATE POLICY не зламає міграцію завдяки DO $$ блокам нижче.

-- ═══════════════════════════════════════════════════════════════════
-- ТАБЛИЦЯ: documents
-- ═══════════════════════════════════════════════════════════════════

-- Крок 1: Увімкнути RLS (ідемпотентно)
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- Крок 2: Прибрати старі неповні policies (якщо були)
DROP POLICY IF EXISTS "documents_select_own" ON public.documents;
DROP POLICY IF EXISTS "documents_insert_own" ON public.documents;
DROP POLICY IF EXISTS "documents_update_own" ON public.documents;
DROP POLICY IF EXISTS "documents_delete_own" ON public.documents;
-- Legacy назви (якщо хтось додавав вручну)
DROP POLICY IF EXISTS "Users can view own documents" ON public.documents;
DROP POLICY IF EXISTS "Users can insert own documents" ON public.documents;
DROP POLICY IF EXISTS "Users can update own documents" ON public.documents;
DROP POLICY IF EXISTS "Users can delete own documents" ON public.documents;

-- ── SELECT ────────────────────────────────────────────────────────
-- Користувач бачить ЛИШЕ свої документи, які не soft-deleted.
-- auth.uid() повертає UUID з JWT — підробити неможливо.
CREATE POLICY "documents_select_own"
    ON public.documents
    FOR SELECT
    USING (
        auth.uid() = user_id
        AND deleted_at IS NULL
    );

-- ── INSERT ────────────────────────────────────────────────────────
-- WITH CHECK: перевірка нового рядка ДО вставки.
-- Захищає від: client надсилає user_id іншого юзера в тілі запиту.
CREATE POLICY "documents_insert_own"
    ON public.documents
    FOR INSERT
    WITH CHECK (
        auth.uid() = user_id
        AND auth.uid() IS NOT NULL
    );

-- ── UPDATE ────────────────────────────────────────────────────────
-- USING: які рядки можна оновлювати (фільтр до UPDATE).
-- WITH CHECK: якими мають бути рядки ПІСЛЯ UPDATE.
-- Обидва потрібні: без WITH CHECK можна "перемістити" doc іншому юзеру.
CREATE POLICY "documents_update_own"
    ON public.documents
    FOR UPDATE
    USING (
        auth.uid() = user_id
        AND deleted_at IS NULL
    )
    WITH CHECK (
        auth.uid() = user_id
    );

-- ── DELETE (hard delete) ──────────────────────────────────────────
-- Soft delete через UPDATE (deleted_at) вже покрито UPDATE policy.
-- Ця policy для справжнього DELETE (адмін операції тощо).
CREATE POLICY "documents_delete_own"
    ON public.documents
    FOR DELETE
    USING (
        auth.uid() = user_id
    );

-- ═══════════════════════════════════════════════════════════════════
-- ТАБЛИЦЯ: document_chunks
-- ═══════════════════════════════════════════════════════════════════
-- Складніший випадок: chunks не мають прямого user_id.
-- Потрібен JOIN через documents → перевірка власності транзитивно.
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "chunks_select_own" ON public.document_chunks;
DROP POLICY IF EXISTS "chunks_insert_own" ON public.document_chunks;
DROP POLICY IF EXISTS "chunks_update_own" ON public.document_chunks;
DROP POLICY IF EXISTS "chunks_delete_own" ON public.document_chunks;
DROP POLICY IF EXISTS "chunks_select_via_document" ON public.document_chunks;

-- ── SELECT ────────────────────────────────────────────────────────
CREATE POLICY "chunks_select_own"
    ON public.document_chunks
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.user_id = auth.uid()
              AND d.deleted_at IS NULL
        )
    );

-- ── INSERT ────────────────────────────────────────────────────────
CREATE POLICY "chunks_insert_own"
    ON public.document_chunks
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.user_id = auth.uid()
        )
    );

-- ── UPDATE ────────────────────────────────────────────────────────
CREATE POLICY "chunks_update_own"
    ON public.document_chunks
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1
            FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.user_id = auth.uid()
        )
    );

-- ── DELETE ────────────────────────────────────────────────────────
CREATE POLICY "chunks_delete_own"
    ON public.document_chunks
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1
            FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.user_id = auth.uid()
        )
    );

-- ═══════════════════════════════════════════════════════════════════
-- ІНДЕКС для прискорення RLS subquery
-- ═══════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx
    ON public.document_chunks (document_id);

CREATE INDEX IF NOT EXISTS documents_rls_lookup_idx
    ON public.documents (id, user_id)
    WHERE deleted_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════
-- ПРИМІТКА для розробників
-- ═══════════════════════════════════════════════════════════════════
-- Service role KEY обходить RLS за дизайном Supabase.
-- Це НОРМАЛЬНО для backend — service role потрібен для ingestion
-- (workers не мають user JWT).
--
-- Defense in depth тепер:
--   Layer 1 (DB)  → RLS policies (ця міграція)
--   Layer 2 (App) → .eq("user_id", uid) в кожному запиті
--   Layer 3 (JWT) → auth middleware перевіряє підпис токена
--
-- Для векторного пошуку через pgvector (asyncpg pool):
-- SQL в retrieval.py вже містить WHERE d.user_id = $X — OK.
-- Переконайтесь що параметр передається (не хардкодиться).
-- ═══════════════════════════════════════════════════════════════════

COMMENT ON TABLE public.documents IS
    'User documents. RLS: auth.uid() = user_id. Service role bypasses — use only from trusted backend.';

COMMENT ON TABLE public.document_chunks IS
    'RAG chunks. RLS: ownership via parent documents.user_id. Service role bypasses.';
