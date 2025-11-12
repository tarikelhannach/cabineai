"""
RAG Chat Service
Feature #2: Chat Inteligente con RAG usando GPT-4o

Implements Retrieval-Augmented Generation (RAG) for intelligent chat:
1. Semantic search using cosine similarity on embeddings
2. Context retrieval from relevant documents
3. GPT-4o generation with citations
4. Multi-language support (Arabic, French, English)
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import ChatConversation, ChatMessage, DocumentEmbedding, Document
from app.services.embedding_service import EmbeddingService
from app.services.cache_service import cache_service


class RAGChatService:
    """Service for RAG-powered chat with semantic document search."""
    
    def __init__(self):
        """Initialize service (OpenAI client loaded lazily when needed)."""
        self._client = None
        self._embedding_service = None
        self.model = "gpt-4o"
        self.max_context_chunks = 5  # Number of relevant chunks to include
        self.max_history_messages = 6  # Previous messages to include for context
    
    def _ensure_openai_client(self):
        """Lazy-load OpenAI client (only when needed for AI operations)."""
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not configured. Please add your OpenAI API key to secrets."
                )
            self._client = OpenAI(api_key=api_key)
        return self._client
    
    def _ensure_embedding_service(self):
        """Lazy-load embedding service (only when needed for RAG operations)."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service
    
    @property
    def client(self):
        """Get OpenAI client (lazy-loaded)."""
        return self._ensure_openai_client()
    
    @property
    def embedding_service(self):
        """Get embedding service (lazy-loaded)."""
        return self._ensure_embedding_service()
    
    def semantic_search(
        self,
        query: str,
        firm_id: int,
        db: Session,
        limit: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for document chunks semantically similar to the query.
        
        Args:
            query: User's search query
            firm_id: Firm ID for tenant isolation
            db: Database session
            limit: Maximum number of results
            min_similarity: Minimum cosine similarity threshold (0-1)
        
        Returns:
            List of relevant chunks with metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_query(query)
        
        # Convert to PostgreSQL array format
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        # Semantic search using cosine similarity with tenant isolation
        sql_query = text("""
            SELECT 
                de.id,
                de.document_id,
                de.chunk_text,
                de.chunk_index,
                d.file_name as document_name,
                d.file_path,
                1 - (de.embedding <=> :query_embedding::vector) as similarity
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            WHERE de.firm_id = :firm_id
            AND 1 - (de.embedding <=> :query_embedding::vector) >= :min_similarity
            ORDER BY de.embedding <=> :query_embedding::vector
            LIMIT :limit
        """)
        
        results = db.execute(
            sql_query,
            {
                "query_embedding": embedding_str,
                "firm_id": firm_id,
                "min_similarity": min_similarity,
                "limit": limit
            }
        ).fetchall()
        
        # Format results
        chunks = []
        for row in results:
            chunks.append({
                "embedding_id": row[0],
                "document_id": row[1],
                "chunk_text": row[2],
                "chunk_index": row[3],
                "document_name": row[4],
                "file_path": row[5],
                "similarity": float(row[6])
            })
        
        return chunks
    
    def _build_system_prompt(self, language: str = "ar") -> str:
        """Build system prompt in the specified language."""
        prompts = {
            "ar": """أنت مساعد قانوني ذكي متخصص في القانون المغربي. مهمتك هي مساعدة المحامين بالإجابة على أسئلتهم بناءً على الوثائق المتوفرة.

تعليمات مهمة:
1. استخدم فقط المعلومات من الوثائق المقدمة في السياق
2. إذا لم تكن المعلومة موجودة في السياق، قل ذلك بوضوح
3. اذكر دائماً مصدر المعلومة (اسم الوثيقة)
4. كن دقيقاً ومحترفاً في إجاباتك
5. إذا كان السؤال غامضاً، اطلب توضيحاً""",
            
            "fr": """Vous êtes un assistant juridique intelligent spécialisé dans le droit marocain. Votre mission est d'aider les avocats en répondant à leurs questions basées sur les documents disponibles.

Instructions importantes:
1. Utilisez uniquement les informations des documents fournis dans le contexte
2. Si l'information n'est pas dans le contexte, dites-le clairement
3. Citez toujours la source de l'information (nom du document)
4. Soyez précis et professionnel dans vos réponses
5. Si la question est ambiguë, demandez des clarifications""",
            
            "en": """You are an intelligent legal assistant specialized in Moroccan law. Your mission is to help lawyers by answering their questions based on available documents.

Important instructions:
1. Use only information from the documents provided in the context
2. If the information is not in the context, say so clearly
3. Always cite the source of information (document name)
4. Be precise and professional in your responses
5. If the question is ambiguous, ask for clarification"""
        }
        return prompts.get(language, prompts["ar"])
    
    def generate_response(
        self,
        conversation_id: int,
        user_message: str,
        firm_id: int,
        user_id: int,
        db: Session,
        language: str = "ar"
    ) -> Dict[str, Any]:
        """
        Generate chat response using RAG.
        
        Args:
            conversation_id: Chat conversation ID
            user_message: User's message
            firm_id: Firm ID for tenant isolation
            user_id: User ID
            db: Database session
            language: Response language (ar, fr, en)
        
        Returns:
            Dict with response and sources
        """
        start_time = time.time()
        
        # Verify conversation belongs to firm
        conversation = db.query(ChatConversation).filter(
            ChatConversation.id == conversation_id,
            ChatConversation.firm_id == firm_id
        ).first()
        
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found for firm {firm_id}")
        
        # Save user message
        user_msg = ChatMessage(
            conversation_id=conversation_id,
            firm_id=firm_id,
            role="user",
            content=user_message
        )
        db.add(user_msg)
        db.commit()
        
        # Semantic search for relevant context
        relevant_chunks = self.semantic_search(
            query=user_message,
            firm_id=firm_id,
            db=db,
            limit=self.max_context_chunks
        )
        
        # Build context from relevant chunks
        context_parts = []
        sources = []
        
        for chunk in relevant_chunks:
            context_parts.append(f"[من الوثيقة: {chunk['document_name']}]\n{chunk['chunk_text']}\n")
            sources.append({
                "document_id": chunk["document_id"],
                "document_name": chunk["document_name"],
                "similarity": chunk["similarity"]
            })
        
        context_text = "\n---\n".join(context_parts) if context_parts else "لا توجد وثائق ذات صلة."
        
        # Get conversation history
        history = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).order_by(ChatMessage.created_at.desc()).limit(self.max_history_messages).all()
        
        history.reverse()  # Chronological order
        
        # Build messages for GPT-4o
        messages = [
            {"role": "system", "content": self._build_system_prompt(language)}
        ]
        
        # Add recent history (exclude the message we just added)
        for msg in history[:-1]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current query with context
        user_prompt = f"""السياق من الوثائق:

{context_text}

---

السؤال: {user_message}"""
        
        messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        # Generate response with GPT-4o
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1500
            )
            
            assistant_message = response.choices[0].message.content
            processing_time = time.time() - start_time
            
            # Save assistant response
            assistant_msg = ChatMessage(
                conversation_id=conversation_id,
                firm_id=firm_id,
                role="assistant",
                content=assistant_message,
                sources=json.dumps(sources, ensure_ascii=False)
            )
            db.add(assistant_msg)
            
            # Update conversation timestamp
            conversation.updated_at = time.time()
            
            db.commit()
            db.refresh(assistant_msg)
            
            return {
                "message_id": assistant_msg.id,
                "content": assistant_message,
                "sources": sources,
                "processing_time_seconds": round(processing_time, 2),
                "chunks_used": len(relevant_chunks)
            }
            
        except OpenAIError as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def create_conversation(
        self,
        title: str,
        firm_id: int,
        user_id: int,
        db: Session
    ) -> ChatConversation:
        """
        Create a new chat conversation.
        
        Args:
            title: Conversation title
            firm_id: Firm ID for tenant isolation
            user_id: User ID
            db: Database session
        
        Returns:
            Created conversation
        """
        conversation = ChatConversation(
            firm_id=firm_id,
            user_id=user_id,
            title=title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    def get_conversations(
        self,
        firm_id: int,
        user_id: int,
        db: Session,
        limit: int = 20
    ) -> List[ChatConversation]:
        """
        Get user's conversations with tenant isolation.
        
        Args:
            firm_id: Firm ID
            user_id: User ID
            db: Database session
            limit: Maximum conversations to return
        
        Returns:
            List of conversations
        """
        return db.query(ChatConversation).filter(
            ChatConversation.firm_id == firm_id,
            ChatConversation.user_id == user_id
        ).order_by(ChatConversation.updated_at.desc()).limit(limit).all()
    
    def get_conversation_messages(
        self,
        conversation_id: int,
        firm_id: int,
        db: Session
    ) -> List[ChatMessage]:
        """
        Get messages from a conversation with tenant isolation.
        
        Args:
            conversation_id: Conversation ID
            firm_id: Firm ID
            db: Database session
        
        Returns:
            List of messages
        """
        # Verify conversation belongs to firm
        conversation = db.query(ChatConversation).filter(
            ChatConversation.id == conversation_id,
            ChatConversation.firm_id == firm_id
        ).first()
        
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found for firm {firm_id}")
        
        return db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.firm_id == firm_id
        ).order_by(ChatMessage.created_at.asc()).all()
