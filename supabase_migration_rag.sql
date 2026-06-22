-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — RAG Pipeline Migration                          ║
-- ║  Run this in Supabase SQL Editor AFTER initial setup      ║
-- ╚══════════════════════════════════════════════════════════════╝

-- 1. Add new columns to reports table
ALTER TABLE reports ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ready';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS chunk_count INTEGER DEFAULT 0;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS analysis JSONB;

-- 2. Create the match_chunks RPC function for vector similarity search
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(3072),
    match_count INT DEFAULT 4,
    filter_report_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id INT,
    report_id UUID,
    chunk_text TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.report_id,
        c.chunk_text,
        c.metadata,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    WHERE (filter_report_id IS NULL OR c.report_id = filter_report_id)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
