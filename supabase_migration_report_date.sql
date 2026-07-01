-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — Store Report Date for Comparison                 ║
-- ║  Run this in Supabase SQL Editor                           ║
-- ╚══════════════════════════════════════════════════════════════╝

-- Add column to store the report's actual date (extracted from document)
-- Separate from uploaded_at (when user uploaded the file)
-- Used for: comparing reports across different test dates
ALTER TABLE reports ADD COLUMN IF NOT EXISTS report_date TEXT;

-- Example:
-- Report A: uploaded_at = 2026-03-01 10:00 AM, report_date = "February 15, 2026"
-- Report B: uploaded_at = 2026-03-05 02:00 PM, report_date = "March 12, 2026"
--
-- Chat can compare using report_date while all dates in chunks are redacted to [DATE]
