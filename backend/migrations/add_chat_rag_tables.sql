-- Migration: Add Chat RAG Tables with pgvector support
-- Feature #2: Chat Inteligente con RAG usando GPT-4o
-- Created: 2025-11-12

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Table: chat_conversations
-- Stores chat conversation sessions for law firms
CREATE TABLE IF NOT EXISTS chat_conversations (
    id SERIAL PRIMARY KEY,
    firm_id INTEGER NOT NULL REFERENCES firms(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for chat_conversations
CREATE INDEX IF NOT EXISTS ix_chat_conversations_firm_id ON chat_conversations(firm_id);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_user_id ON chat_conversations(user_id);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_firm_id_updated_at ON chat_conversations(firm_id, updated_at DESC);

-- Table: chat_messages
-- Stores individual messages within conversations
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    firm_id INTEGER NOT NULL REFERENCES firms(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    sources TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chat_messages_role_check CHECK (role IN ('user', 'assistant'))
);

-- Indexes for chat_messages
CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_firm_id ON chat_messages(firm_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id_created_at ON chat_messages(conversation_id, created_at ASC);

-- Table: document_embeddings
-- Stores vector embeddings for document chunks (RAG retrieval)
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    firm_id INTEGER NOT NULL REFERENCES firms(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for document_embeddings
CREATE INDEX IF NOT EXISTS ix_document_embeddings_document_id ON document_embeddings(document_id);
CREATE INDEX IF NOT EXISTS ix_document_embeddings_firm_id ON document_embeddings(firm_id);
CREATE INDEX IF NOT EXISTS ix_document_embeddings_firm_id_document_id ON document_embeddings(firm_id, document_id);

-- Vector similarity index for fast nearest neighbor search (cosine distance)
-- This is critical for RAG performance
-- Using HNSW (Hierarchical Navigable Small World) instead of IVFFlat because:
-- 1. HNSW supports >2000 dimensions (text-embedding-3-large = 3072 dims)
-- 2. HNSW is faster for queries and more accurate
-- 3. HNSW is the recommended index for production RAG systems
CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding_cosine ON document_embeddings 
USING hnsw (embedding vector_cosine_ops);

-- Unique constraint to prevent duplicate embeddings
CREATE UNIQUE INDEX IF NOT EXISTS ix_document_embeddings_unique ON document_embeddings(document_id, chunk_index);

-- Comments for documentation
COMMENT ON TABLE chat_conversations IS 'Chat conversation sessions with GPT-4o RAG';
COMMENT ON TABLE chat_messages IS 'Individual messages in chat conversations';
COMMENT ON TABLE document_embeddings IS 'Vector embeddings for semantic search using text-embedding-3-large';
COMMENT ON COLUMN document_embeddings.embedding IS '1536-dimensional vector from OpenAI text-embedding-3-large (dimensions=1536 for pgvector compatibility)';
COMMENT ON INDEX ix_document_embeddings_embedding_cosine IS 'IVFFlat index for fast cosine similarity search in RAG queries';
