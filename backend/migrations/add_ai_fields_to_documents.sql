-- Migration: Add AI processing fields to documents table
-- Created: 2025-01-21
-- Description: Adds fields for DeepSeek AI integration (classification, metadata, summary)

-- Add AI processing columns to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_summary TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_classification VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_metadata JSONB;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_processed BOOLEAN DEFAULT FALSE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_processed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ai_error TEXT;

-- Create indexes CONCURRENTLY to avoid table locks (production-safe)
-- Note: CONCURRENTLY requires running outside a transaction block
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_ai_classification ON documents(ai_classification);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_ai_processed ON documents(ai_processed);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_ai_metadata ON documents USING GIN (ai_metadata);

-- Add comment for documentation
COMMENT ON COLUMN documents.ai_summary IS 'AI-generated executive summary of document content';
COMMENT ON COLUMN documents.ai_classification IS 'AI classification: Contrat, Jugement, Facture, Statuts, etc.';
COMMENT ON COLUMN documents.ai_metadata IS 'Extracted metadata: parties, dates, case numbers, amounts';
COMMENT ON COLUMN documents.ai_processed IS 'Whether AI processing has been completed';
COMMENT ON COLUMN documents.ai_processed_at IS 'Timestamp when AI processing completed';
COMMENT ON COLUMN documents.ai_error IS 'Error message if AI processing failed';
