-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — Update embedding dimensions to 3072             ║
-- ║  Run this in Supabase SQL Editor to upgrade the schema    ║
-- ╚══════════════════════════════════════════════════════════════╝

-- Update chunks table embedding column from VECTOR(768) to VECTOR(3072)
-- for gemini-embedding-001 model (3072-dimensional embeddings)

ALTER TABLE chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE chunks ADD COLUMN embedding VECTOR(3072);

-- Recreate the ivfflat index on the new embedding column
DROP INDEX IF EXISTS idx_chunks_embedding;
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops);
