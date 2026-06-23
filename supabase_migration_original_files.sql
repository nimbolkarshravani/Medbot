-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — Store Original Files for PDF Rendering            ║
-- ║  Run this in Supabase SQL Editor                            ║
-- ╚══════════════════════════════════════════════════════════════╝

-- Add original_file column to reports (stores base64 encoded files)
ALTER TABLE reports ADD COLUMN IF NOT EXISTS original_file TEXT;
