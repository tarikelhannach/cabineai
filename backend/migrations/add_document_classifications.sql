-- Migration: Add document_classifications table for AI classification feature
-- Date: 2025-11-12
-- Description: Table to store GPT-4o classification results for documents

CREATE TABLE IF NOT EXISTS document_classifications (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    firm_id INTEGER NOT NULL REFERENCES firms(id) ON DELETE CASCADE,
    
    -- Classification results from GPT-4o
    document_type VARCHAR(100),
    legal_area VARCHAR(200),
    parties_involved TEXT,
    important_dates TEXT,
    urgency_level VARCHAR(50),
    summary TEXT,
    keywords TEXT,
    
    -- AI metadata
    model_used VARCHAR(50) DEFAULT 'gpt-4o',
    confidence_score REAL,
    processing_time_seconds REAL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    classified_by INTEGER REFERENCES users(id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_document_classifications_document_id ON document_classifications(document_id);
CREATE INDEX IF NOT EXISTS idx_document_classifications_firm_id ON document_classifications(firm_id);
CREATE INDEX IF NOT EXISTS idx_document_classifications_document_type ON document_classifications(document_type);
CREATE INDEX IF NOT EXISTS idx_document_classifications_legal_area ON document_classifications(legal_area);

-- Add unique constraint to prevent duplicate classifications
CREATE UNIQUE INDEX IF NOT EXISTS unique_document_classification ON document_classifications(document_id, firm_id);

COMMENT ON TABLE document_classifications IS 'Stores AI-powered classification results for legal documents using GPT-4o';
COMMENT ON COLUMN document_classifications.document_type IS 'Type of document (contract, court ruling, memo, etc.)';
COMMENT ON COLUMN document_classifications.legal_area IS 'Legal area (civil, criminal, commercial, administrative, etc.)';
COMMENT ON COLUMN document_classifications.parties_involved IS 'JSON array of party names involved in the document';
COMMENT ON COLUMN document_classifications.important_dates IS 'JSON array of important dates extracted from the document';
COMMENT ON COLUMN document_classifications.urgency_level IS 'Urgency level: normal, medium, urgent, very_urgent';
COMMENT ON COLUMN document_classifications.summary IS 'Brief summary of the document (2-3 sentences)';
COMMENT ON COLUMN document_classifications.keywords IS 'JSON array of important keywords';
COMMENT ON COLUMN document_classifications.model_used IS 'AI model used for classification (e.g., gpt-4o)';
COMMENT ON COLUMN document_classifications.confidence_score IS 'Confidence score of the classification (0.0-1.0)';
COMMENT ON COLUMN document_classifications.processing_time_seconds IS 'Time taken to classify the document in seconds';
