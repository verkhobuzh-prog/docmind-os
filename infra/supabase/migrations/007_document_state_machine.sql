-- Document State Machine — event log table

CREATE TABLE IF NOT EXISTS public.document_events (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id uuid NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id uuid NOT NULL,
    from_state text NOT NULL,
    to_state text NOT NULL,
    event text NOT NULL,
    error_code text,
    error_message text,
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS doc_events_doc_idx
    ON public.document_events (document_id, created_at DESC);
CREATE INDEX IF NOT EXISTS doc_events_user_idx
    ON public.document_events (user_id, created_at DESC);

-- Додай колонки до documents якщо немає
ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS retry_count int NOT NULL DEFAULT 0;
ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS error_code text;
ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS last_event text;

-- RLS
ALTER TABLE public.document_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "events_select_own" ON public.document_events;
CREATE POLICY "events_select_own" ON public.document_events
    FOR SELECT USING (user_id = auth.uid());
