-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — Update embedding model to gemini-embedding-2   ║
-- ║  Run this in Supabase SQL Editor to upgrade the schema    ║
-- ╚══════════════════════════════════════════════════════════════╝

-- Drop any existing embeddings and reset to 768 dims for gemini-embedding-2
ALTER TABLE chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE chunks ADD COLUMN embedding VECTOR(768);

-- Recreate the ivfflat index on the new embedding column
DROP INDEX IF EXISTS idx_chunks_embedding;
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops);
