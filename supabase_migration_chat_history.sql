-- ╔══════════════════════════════════════════════════════════════╗
-- ║  MedBot — Chat History Table                             ║
-- ║  Run this in Supabase SQL Editor                          ║
-- ╚══════════════════════════════════════════════════════════════╝

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    referenced_report_ids UUID[] DEFAULT ARRAY[]::UUID[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- RLS: users can only read/write their own messages
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own messages"
    ON chat_messages FOR SELECT
    USING (patient_id = auth.uid());

CREATE POLICY "Users can insert own messages"
    ON chat_messages FOR INSERT
    WITH CHECK (patient_id = auth.uid());

-- Index for fast message retrieval by user and date
CREATE INDEX IF NOT EXISTS idx_chat_messages_patient_created
    ON chat_messages(patient_id, created_at DESC);
