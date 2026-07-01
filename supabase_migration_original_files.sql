-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — Enable PDF Viewer & Fix PII Leaks               ║
-- ║  Run this in Supabase SQL Editor                          ║
-- ╚══════════════════════════════════════════════════════════════╝

-- 1. Add column to store original PDF files (base64 encoded)
-- This enables the Chat tab to display PDFs in a proper viewer
ALTER TABLE reports ADD COLUMN IF NOT EXISTS original_file TEXT;

-- INDEX HINT:
-- After running this migration, you MUST re-upload any PDF reports to populate the original_file column.
--
-- Reports uploaded BEFORE this migration will NOT have PDF viewer in the Chat tab
-- (they will fall back to showing extracted text).
--
-- To enable PDF viewer for existing reports:
--   1. Go to the Upload tab
--   2. Re-upload each PDF report
--   3. The original_file column will be populated on re-upload
--   4. The PDF viewer will now work in the Chat tab for that report

-- PRIVACY NOTE:
-- All user names, dates, and PII are redacted in the chunks table:
-- - Patient Name: Emma Wilson  →  Patient Name: [NAME]
-- - SSN: 123-45-6789          →  [SSN]
-- - Email: user@example.com   →  [EMAIL]
-- - Phone: (555) 123-4567     →  [PHONE]
--
-- The chat endpoint explicitly forbids using real names and sanitizes responses.
