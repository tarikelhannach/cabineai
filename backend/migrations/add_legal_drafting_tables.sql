-- Migration: Add Legal Drafting Assistant Tables
-- Feature #3: Asistente de Redacción Legal
-- Tables: document_templates, generated_documents

-- Create enum types for legal document drafting
CREATE TYPE legal_document_type AS ENUM ('acta', 'demanda', 'contrato', 'poder', 'escrito', 'dictamen', 'other');
CREATE TYPE draft_status AS ENUM ('draft', 'reviewed', 'approved', 'rejected');

-- Document Templates table
-- Stores reusable templates for legal documents with placeholders
CREATE TABLE IF NOT EXISTS document_templates (
    id SERIAL PRIMARY KEY,
    firm_id INTEGER NOT NULL REFERENCES firms(id) ON DELETE CASCADE,
    
    template_type legal_document_type NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    template_content TEXT NOT NULL,  -- Arabic template with {{placeholders}}
    placeholders TEXT,  -- JSON array of placeholder names and descriptions
    
    is_default BOOLEAN DEFAULT FALSE,  -- System-provided templates
    is_active BOOLEAN DEFAULT TRUE,
    
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for document_templates
CREATE INDEX ix_document_templates_firm_id ON document_templates(firm_id);
CREATE INDEX ix_document_templates_template_type ON document_templates(template_type);
CREATE INDEX ix_document_templates_firm_id_type ON document_templates(firm_id, template_type);

-- Generated Documents table
-- Stores AI-generated legal documents with workflow tracking
CREATE TABLE IF NOT EXISTS generated_documents (
    id SERIAL PRIMARY KEY,
    firm_id INTEGER NOT NULL REFERENCES firms(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES document_templates(id) ON DELETE SET NULL,
    expediente_id INTEGER REFERENCES cases(id) ON DELETE SET NULL,
    
    document_type legal_document_type NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,  -- Generated Arabic document
    
    status draft_status DEFAULT 'draft' NOT NULL,
    
    -- User input and AI metadata
    user_input TEXT,  -- Original user prompt/parameters
    metadata TEXT,  -- JSON with placeholders filled, generation params
    model_used VARCHAR(50) DEFAULT 'gpt-4o',
    generation_time_seconds FLOAT,
    
    -- Workflow tracking
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    review_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    approved_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for generated_documents
CREATE INDEX ix_generated_documents_firm_id ON generated_documents(firm_id);
CREATE INDEX ix_generated_documents_template_id ON generated_documents(template_id);
CREATE INDEX ix_generated_documents_expediente_id ON generated_documents(expediente_id);
CREATE INDEX ix_generated_documents_document_type ON generated_documents(document_type);
CREATE INDEX ix_generated_documents_status ON generated_documents(status);
CREATE INDEX ix_generated_documents_firm_id_status ON generated_documents(firm_id, status);
CREATE INDEX ix_generated_documents_firm_id_created_by ON generated_documents(firm_id, created_by);
CREATE INDEX ix_generated_documents_created_by ON generated_documents(created_by);

-- Comment documentation
COMMENT ON TABLE document_templates IS 'Reusable templates for legal document generation with AI';
COMMENT ON TABLE generated_documents IS 'AI-generated legal documents with review workflow tracking';
COMMENT ON COLUMN document_templates.template_content IS 'Arabic template text with {{placeholder}} markers for GPT-4o';
COMMENT ON COLUMN generated_documents.content IS 'Final generated document in Arabic';
COMMENT ON COLUMN generated_documents.user_input IS 'Original user parameters/prompt for document generation';
