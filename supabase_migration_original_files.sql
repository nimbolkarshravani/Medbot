-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — Store Original Report Files (base64)              ║
-- ║  Run this in Supabase SQL Editor                            ║
-- ╚══════════════════════════════════════════════════════════════╝

-- Store original file as base64 for PDF rendering in the viewer
ALTER TABLE reports ADD COLUMN IF NOT EXISTS original_file TEXT;
