-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — Supabase Database Setup                          ║
-- ║  Run this in Supabase SQL Editor (one-time setup)          ║
-- ╚══════════════════════════════════════════════════════════════╝

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create tables
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT auth.uid(),
    created_at TIMESTAMP DEFAULT NOW(),
    email TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    source_type TEXT,
    file_name TEXT,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    chunk_text TEXT,
    embedding VECTOR(3072),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_patient ON chunks (patient_id);

-- 4. Enable Row-Level Security
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports  ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks   ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies — users can only access their own data

-- patients: auto-create row on first login, read own data
CREATE POLICY "Users can read own patient record"
    ON patients FOR SELECT
    USING (id = auth.uid());

CREATE POLICY "Users can insert own patient record"
    ON patients FOR INSERT
    WITH CHECK (id = auth.uid());

-- reports: full CRUD on own reports
CREATE POLICY "Users can read own reports"
    ON reports FOR SELECT
    USING (patient_id = auth.uid());

CREATE POLICY "Users can insert own reports"
    ON reports FOR INSERT
    WITH CHECK (patient_id = auth.uid());

CREATE POLICY "Users can delete own reports"
    ON reports FOR DELETE
    USING (patient_id = auth.uid());

-- chunks: read/insert own chunks
CREATE POLICY "Users can read own chunks"
    ON chunks FOR SELECT
    USING (patient_id = auth.uid());

CREATE POLICY "Users can insert own chunks"
    ON chunks FOR INSERT
    WITH CHECK (patient_id = auth.uid());

CREATE POLICY "Users can delete own chunks"
    ON chunks FOR DELETE
    USING (patient_id = auth.uid());

-- 6. Auto-create patient record on signup (trigger)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.patients (id, email)
    VALUES (NEW.id, NEW.email)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
