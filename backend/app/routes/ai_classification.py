"""
AI Classification Routes - API endpoints for document classification using GPT-4o
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import json

from app.database import get_db
from app.auth.jwt import get_current_user
from app.models import User, DocumentClassification
from app.services.ai_classification_service import AIClassificationService

router = APIRouter(prefix="/api/documents", tags=["AI Classification"])


class ClassificationRequest(BaseModel):
    force_reclassify: bool = False


class ClassificationResponse(BaseModel):
    id: int
    document_id: int
    document_type: Optional[str]
    legal_area: Optional[str]
    parties_involved: List[str]
    important_dates: List[str]
    urgency_level: Optional[str]
    summary: Optional[str]
    keywords: List[str]
    model_used: str
    confidence_score: Optional[float]
    processing_time_seconds: Optional[float]
    created_at: str
    
    class Config:
        from_attributes = True
    
    @staticmethod
    def from_model(classification: DocumentClassification) -> "ClassificationResponse":
        """Convert database model to response"""
        return ClassificationResponse(
            id=classification.id,
            document_id=classification.document_id,
            document_type=classification.document_type,
            legal_area=classification.legal_area,
            parties_involved=json.loads(classification.parties_involved) if classification.parties_involved else [],
            important_dates=json.loads(classification.important_dates) if classification.important_dates else [],
            urgency_level=classification.urgency_level,
            summary=classification.summary,
            keywords=json.loads(classification.keywords) if classification.keywords else [],
            model_used=classification.model_used or "gpt-4o",
            confidence_score=classification.confidence_score,
            processing_time_seconds=classification.processing_time_seconds,
            created_at=classification.created_at.isoformat() if classification.created_at else ""
        )


@router.post("/{document_id}/classify", response_model=ClassificationResponse)
async def classify_document(
    document_id: int,
    request: ClassificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Classify a document using GPT-4o
    
    Extracts:
    - Document type
    - Legal area
    - Parties involved
    - Important dates
    - Urgency level
    - Summary
    - Keywords
    """
    
    service = AIClassificationService()
    
    try:
        classification = await service.classify_document(
            db=db,
            document_id=document_id,
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            force_reclassify=request.force_reclassify
        )
        
        return ClassificationResponse.from_model(classification)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification failed: {str(e)}"
        )


@router.get("/{document_id}/classification", response_model=Optional[ClassificationResponse])
async def get_classification(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get existing classification for a document"""
    
    service = AIClassificationService()
    classification = service.get_classification(
        db=db,
        document_id=document_id,
        firm_id=current_user.firm_id
    )
    
    if not classification:
        return None
    
    return ClassificationResponse.from_model(classification)
