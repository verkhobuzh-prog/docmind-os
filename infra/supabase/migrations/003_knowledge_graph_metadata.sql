-- DocMind OS — Knowledge graph metadata (semantic triples audit / provenance)

CREATE TABLE IF NOT EXISTS public.semantic_triples (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id uuid NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    chunk_id uuid REFERENCES public.document_chunks(id) ON DELETE SET NULL,
    subject text NOT NULL,
    subject_type text NOT NULL,
    predicate text NOT NULL,
    object_ text NOT NULL,
    object_type text NOT NULL,
    confidence float NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    evidence_quote text,
    valid_from timestamptz,
    valid_to timestamptz,
    extraction_model text,
    validation_status text NOT NULL DEFAULT 'auto-extracted'
        CHECK (validation_status IN ('auto-extracted', 'human-verified', 'disputed')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS triples_doc_idx ON public.semantic_triples (doc_id);
CREATE INDEX IF NOT EXISTS triples_subject_idx ON public.semantic_triples (subject);
CREATE INDEX IF NOT EXISTS triples_predicate_idx ON public.semantic_triples (predicate);

-- RLS: доступ через батьківський документ
ALTER TABLE public.semantic_triples ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "triples_select_via_document" ON public.semantic_triples;
CREATE POLICY "triples_select_via_document" ON public.semantic_triples FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.documents d
        WHERE d.id = semantic_triples.doc_id
          AND d.user_id = auth.uid()
          AND d.deleted_at IS NULL
    ));
