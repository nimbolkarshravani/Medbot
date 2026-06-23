-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — Supabase Storage for Original Report Files        ║
-- ║  Run this in Supabase SQL Editor                            ║
-- ╚══════════════════════════════════════════════════════════════╝

-- 1. Add URL column for original file storage
ALTER TABLE reports ADD COLUMN IF NOT EXISTS original_file_url TEXT;

-- 2. Create the storage bucket (run this via Supabase Dashboard > Storage > New Bucket)
-- Bucket name: "reports"
-- Public: OFF
-- File size limit: 20MB
-- Allowed MIME types: application/pdf, text/plain

-- 3. RLS policies for storage (run in SQL Editor)
-- Allow authenticated users to upload to their own folder
CREATE POLICY "Users can upload own reports"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'reports'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

-- Allow authenticated users to read their own files
CREATE POLICY "Users can read own reports"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'reports'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

-- Allow authenticated users to delete their own files
CREATE POLICY "Users can delete own reports"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'reports'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );
