"""
Chat RAG API Routes
Feature #2: Chat Inteligente con RAG usando GPT-4o

Endpoints for intelligent chat with semantic document search.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.auth.jwt import get_current_user
from app.models import User, ChatConversation, ChatMessage
from app.services.rag_chat_service import RAGChatService
from app.services.embedding_service import EmbeddingService


router = APIRouter(prefix="/api/chat", tags=["Chat RAG"])


# Pydantic schemas
class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


class ConversationResponse(BaseModel):
    id: int
    firm_id: int
    user_id: int
    title: str
    created_at: str
    updated_at: str
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    sources: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    conversation_id: int
    message: str = Field(..., min_length=1, max_length=5000)
    language: Optional[str] = "ar"  # ar, fr, en


class SendMessageResponse(BaseModel):
    message_id: int
    content: str
    sources: List[dict]
    processing_time_seconds: float
    chunks_used: int


class EmbedDocumentRequest(BaseModel):
    force_regenerate: Optional[bool] = False


class EmbedDocumentResponse(BaseModel):
    document_id: int
    document_name: str
    chunks_embedded: int
    total_chunks: int
    processing_time_seconds: float
    status: str


# Routes
@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new chat conversation.
    
    Requires: LAWYER, ASSISTANT, or ADMIN role
    """
    try:
        service = RAGChatService()
        conversation = service.create_conversation(
            title=conversation_data.title,
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            db=db
        )
        
        return {
            **conversation.__dict__,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "message_count": 0
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/conversations", response_model=List[ConversationResponse])
def get_conversations(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's chat conversations.
    
    Requires: LAWYER, ASSISTANT, or ADMIN role
    """
    try:
        service = RAGChatService()
        conversations = service.get_conversations(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            db=db,
            limit=limit
        )
        
        result = []
        for conv in conversations:
            # Count messages
            message_count = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conv.id
            ).count()
            
            result.append({
                **conv.__dict__,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": message_count
            })
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get messages from a conversation.
    
    Requires: LAWYER, ASSISTANT, or ADMIN role
    Tenant isolation: Only returns messages from user's firm
    """
    try:
        service = RAGChatService()
        messages = service.get_conversation_messages(
            conversation_id=conversation_id,
            firm_id=current_user.firm_id,
            db=db
        )
        
        return [
            {
                **msg.__dict__,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/messages", response_model=SendMessageResponse)
def send_message(
    message_data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message and get AI response with RAG.
    
    Requires: LAWYER, ASSISTANT, or ADMIN role
    Tenant isolation: Only searches documents from user's firm
    """
    try:
        service = RAGChatService()
        response = service.generate_response(
            conversation_id=message_data.conversation_id,
            user_message=message_data.message,
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            db=db,
            language=message_data.language
        )
        
        return response
    except ValueError as e:
        # Check if it's an API key error (case-insensitive)
        error_msg = str(e).lower()
        if "api key" in error_msg or "openai" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API key not configured. Please contact your administrator."
            )
        # Otherwise it's a validation error (conversation not found, etc.)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/documents/{document_id}/embed", response_model=EmbedDocumentResponse)
def embed_document(
    document_id: int,
    request_data: EmbedDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate embeddings for a document (required for RAG search).
    
    Requires: LAWYER, ASSISTANT, or ADMIN role
    Tenant isolation: Only embeds documents from user's firm
    """
    try:
        service = EmbeddingService()
        result = service.embed_document(
            document_id=document_id,
            firm_id=current_user.firm_id,
            db=db,
            force_regenerate=request_data.force_regenerate
        )
        
        return result
    except ValueError as e:
        # Check if it's an API key error (case-insensitive)
        error_msg = str(e).lower()
        if "api key" in error_msg or "openai" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API key not configured. Please contact your administrator."
            )
        # Otherwise it's a validation error (document not found, etc.)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
