"""
Embedding Service for RAG Chat
Feature #2: Chat Inteligente con RAG usando GPT-4o

Generates vector embeddings for document chunks using OpenAI text-embedding-3-large.
Optimized for Arabic documents with 1536 dimensions (pgvector compatibility).
"""

import os
import time
from typing import List, Dict, Any
from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session
from app.models import Document, DocumentEmbedding
from app.services.cache_service import cache_service


class EmbeddingService:
    """Service for generating and managing document embeddings for semantic search."""
    
    def __init__(self):
        """Initialize service (OpenAI client loaded lazily when needed)."""
        self._client = None
        self.model = "text-embedding-3-large"
        self.dimensions = 1536  # Optimized for pgvector HNSW index
        self.chunk_size = 500  # Words per chunk
        self.chunk_overlap = 50  # Words overlap between chunks
    
    def _ensure_openai_client(self):
        """Lazy-load OpenAI client (only when needed for embedding operations)."""
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not configured. Please add your OpenAI API key to secrets."
                )
            self._client = OpenAI(api_key=api_key)
        return self._client
    
    @property
    def client(self):
        """Get OpenAI client (lazy-loaded)."""
        return self._ensure_openai_client()
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks for better semantic coverage.
        
        Args:
            text: Full document text
        
        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk = " ".join(chunk_words)
            if len(chunk.strip()) > 100:  # Minimum chunk size (characters)
                chunks.append(chunk)
        
        return chunks if chunks else [text]  # Return full text if too short
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text chunk with caching.
        
        Args:
            text: Text to embed
        
        Returns:
            1536-dimensional vector
        
        Raises:
            Exception: If OpenAI API call fails
        """
        cached = cache_service.get_embedding(text, self.model)
        if cached is not None:
            return cached
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions
            )
            embedding = response.data[0].embedding
            cache_service.set_embedding(text, embedding, self.model)
            return embedding
        except OpenAIError as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def embed_document(
        self,
        document_id: int,
        firm_id: int,
        db: Session,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate and store embeddings for a document.
        
        Args:
            document_id: Document ID to embed
            firm_id: Firm ID for tenant isolation
            db: Database session
            force_regenerate: If True, delete existing embeddings and regenerate
        
        Returns:
            Dict with embedding stats
        
        Raises:
            ValueError: If document not found or has no OCR text
        """
        # Get document with tenant isolation
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.firm_id == firm_id
        ).first()
        
        if not document:
            raise ValueError(f"Document {document_id} not found for firm {firm_id}")
        
        # Check OCR text
        if not document.ocr_text or len(document.ocr_text.strip()) < 100:
            raise ValueError(
                "Document has no OCR text or text too short. Run OCR first."
            )
        
        # Check if already embedded
        existing_count = db.query(DocumentEmbedding).filter(
            DocumentEmbedding.document_id == document_id,
            DocumentEmbedding.firm_id == firm_id
        ).count()
        
        if existing_count > 0 and not force_regenerate:
            return {
                "document_id": document_id,
                "chunks_embedded": existing_count,
                "status": "already_embedded",
                "message": "Document already has embeddings. Use force_regenerate=True to regenerate."
            }
        
        # Delete existing embeddings if regenerating
        if force_regenerate:
            db.query(DocumentEmbedding).filter(
                DocumentEmbedding.document_id == document_id,
                DocumentEmbedding.firm_id == firm_id
            ).delete()
        
        # Chunk the document
        chunks = self.chunk_text(document.ocr_text)
        
        # Generate embeddings for each chunk
        start_time = time.time()
        embeddings_created = 0
        
        for idx, chunk in enumerate(chunks):
            try:
                # Generate embedding
                embedding_vector = self.generate_embedding(chunk)
                
                # Store in database
                doc_embedding = DocumentEmbedding(
                    document_id=document_id,
                    firm_id=firm_id,
                    chunk_text=chunk,
                    chunk_index=idx,
                    embedding=embedding_vector
                )
                db.add(doc_embedding)
                embeddings_created += 1
                
            except Exception as e:
                print(f"Error embedding chunk {idx}: {str(e)}")
                continue
        
        db.commit()
        processing_time = time.time() - start_time
        
        return {
            "document_id": document_id,
            "document_name": document.file_name,
            "chunks_embedded": embeddings_created,
            "total_chunks": len(chunks),
            "processing_time_seconds": round(processing_time, 2),
            "status": "success"
        }
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
        
        Returns:
            1536-dimensional vector
        """
        return self.generate_embedding(query)
