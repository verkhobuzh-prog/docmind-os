-- Phase 3: User profiles & subjects

CREATE TABLE IF NOT EXISTS subjects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,  -- education | legal | business | technical | medical
    level       TEXT,           -- beginner | intermediate | advanced (для освіти)
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO subjects (name, category, level) VALUES
  ('Алгебра',            'education', 'intermediate'),
  ('Геометрія',          'education', 'intermediate'),
  ('Фізика',             'education', 'advanced'),
  ('Хімія',              'education', 'advanced'),
  ('Українська мова',    'education', 'beginner'),
  ('Історія України',    'education', 'intermediate'),
  ('Біологія',           'education', 'intermediate'),
  ('Інформатика',        'education', 'intermediate'),
  ('Цивільне право',     'legal',     NULL),
  ('Трудове право',      'legal',     NULL),
  ('Корпоративне право', 'legal',     NULL),
  ('Бухгалтерія',        'business',  NULL),
  ('Логістика',          'business',  NULL),
  ('HR та кадри',        'business',  NULL),
  ('Менеджмент',         'business',  NULL),
  ('Медицина',           'medical',   NULL),
  ('Технічна документація', 'technical', NULL)
;

CREATE TABLE IF NOT EXISTS user_profiles (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    complexity_level  INTEGER NOT NULL DEFAULT 3 CHECK (complexity_level BETWEEN 1 AND 5),
    domain            TEXT NOT NULL DEFAULT 'general',
    is_active         BOOLEAN NOT NULL DEFAULT FALSE,
    preferences       JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS user_profiles_one_active
    ON user_profiles (user_id)
    WHERE is_active = TRUE;

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_profiles_own" ON user_profiles;
CREATE POLICY "user_profiles_own" ON user_profiles
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS subject_id UUID REFERENCES subjects(id),
    ADD COLUMN IF NOT EXISTS topic TEXT,
    ADD COLUMN IF NOT EXISTS complexity_suggested INTEGER;

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_profiles_updated_at ON user_profiles;
CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
