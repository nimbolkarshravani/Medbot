-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — RAG Pipeline Migration                          ║
-- ║  Run this in Supabase SQL Editor AFTER initial setup      ║
-- ╚══════════════════════════════════════════════════════════════╝

-- 1. Add new columns to reports table
ALTER TABLE reports ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ready';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS chunk_count INTEGER DEFAULT 0;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS analysis JSONB;

-- 2. Create the match_chunks RPC function for cross-report vector search
-- Retrieves relevant chunks across ALL of a patient's reports
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(768),
    patient_id_filter UUID,
    match_count INT DEFAULT 8
)
RETURNS TABLE (
    chunk_text TEXT,
    report_id UUID,
    similarity FLOAT,
    uploaded_at TIMESTAMP
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.chunk_text,
        c.report_id,
        1 - (c.embedding <=> query_embedding) AS similarity,
        r.uploaded_at
    FROM chunks c
    JOIN reports r ON c.report_id = r.id
    WHERE c.patient_id = patient_id_filter
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
