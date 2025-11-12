"""
Legal Document Drafting API Routes
Endpoints for AI-powered legal document generation using GPT-4o
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..auth.jwt import get_current_user, require_role
from ..models import (
    User, DocumentTemplate, GeneratedDocument, 
    LegalDocumentType, DraftStatus, UserRole
)
from ..services.document_drafting_service import DocumentDraftingService


router = APIRouter(prefix="/api/drafting", tags=["Legal Document Drafting"])


# ==================== Pydantic Schemas ====================

class TemplateCreate(BaseModel):
    template_type: str
    name: str
    description: Optional[str] = None
    template_content: str
    placeholders: Optional[str] = None  # JSON string

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_content: Optional[str] = None
    placeholders: Optional[str] = None
    is_active: Optional[bool] = None

class GenerateFromTemplateRequest(BaseModel):
    template_id: int
    placeholders: dict  # Key-value pairs for placeholder replacement
    expediente_id: Optional[int] = None
    additional_instructions: Optional[str] = None

class GenerateFromPromptRequest(BaseModel):
    document_type: str
    user_prompt: str
    expediente_id: Optional[int] = None
    context: Optional[dict] = None

class UpdateStatusRequest(BaseModel):
    status: str
    review_notes: Optional[str] = None

class TemplateResponse(BaseModel):
    id: int
    firm_id: int
    template_type: str
    name: str
    description: Optional[str]
    template_content: str
    placeholders: Optional[str]
    is_default: bool
    is_active: bool
    created_by: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class GeneratedDocumentResponse(BaseModel):
    id: int
    firm_id: int
    template_id: Optional[int]
    expediente_id: Optional[int]
    document_type: str
    title: str
    content: str
    status: str
    user_input: Optional[str]
    generation_metadata: Optional[str]
    model_used: str
    generation_time_seconds: Optional[float]
    created_by: int
    reviewed_by: Optional[int]
    approved_by: Optional[int]
    review_notes: Optional[str]
    created_at: str
    updated_at: str
    reviewed_at: Optional[str]
    approved_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== Document Generation Endpoints ====================

@router.post("/generate/template", response_model=GeneratedDocumentResponse)
def generate_from_template(
    request: GenerateFromTemplateRequest,
    current_user: User = Depends(require_role(["lawyer", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Generate a legal document from a template with placeholder replacement.
    
    Requires: LAWYER or ADMIN role
    Uses: GPT-4o for document polishing and enhancement
    """
    try:
        service = DocumentDraftingService()
        result = service.generate_from_template(
            template_id=request.template_id,
            placeholders=request.placeholders,
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            db=db,
            expediente_id=request.expediente_id,
            additional_instructions=request.additional_instructions
        )
        
        return GeneratedDocumentResponse(
            **{k: v for k, v in result.__dict__.items() if not k.startswith('_')},
            created_at=result.created_at.isoformat(),
            updated_at=result.updated_at.isoformat(),
            reviewed_at=result.reviewed_at.isoformat() if result.reviewed_at else None,
            approved_at=result.approved_at.isoformat() if result.approved_at else None
        )
    except ValueError as e:
        # Check if it's an API key error (case-insensitive)
        error_msg = str(e).lower()
        if "api key" in error_msg or "openai" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API key not configured. Please contact your administrator."
            )
        # Otherwise it's a validation error (template not found, etc.)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/generate/prompt", response_model=GeneratedDocumentResponse)
def generate_from_prompt(
    request: GenerateFromPromptRequest,
    current_user: User = Depends(require_role(["lawyer", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Generate a legal document from a free-form user prompt.
    
    Requires: LAWYER or ADMIN role
    Uses: GPT-4o for complete document generation
    """
    try:
        # Convert string to enum
        try:
            doc_type = LegalDocumentType(request.document_type.lower())
        except ValueError:
            raise ValueError(f"Invalid document type: {request.document_type}")
        
        service = DocumentDraftingService()
        result = service.generate_from_prompt(
            document_type=doc_type,
            user_prompt=request.user_prompt,
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            db=db,
            expediente_id=request.expediente_id,
            context=request.context
        )
        
        return GeneratedDocumentResponse(
            **{k: v for k, v in result.__dict__.items() if not k.startswith('_')},
            created_at=result.created_at.isoformat(),
            updated_at=result.updated_at.isoformat(),
            reviewed_at=result.reviewed_at.isoformat() if result.reviewed_at else None,
            approved_at=result.approved_at.isoformat() if result.approved_at else None
        )
    except ValueError as e:
        # Check if it's an API key error (case-insensitive)
        error_msg = str(e).lower()
        if "api key" in error_msg or "openai" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API key not configured. Please contact your administrator."
            )
        # Otherwise it's a validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== Generated Documents Management ====================

@router.get("/documents", response_model=List[GeneratedDocumentResponse])
def list_generated_documents(
    status_filter: Optional[str] = None,
    document_type: Optional[str] = None,
    expediente_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_role(["lawyer", "assistant", "admin"])),
    db: Session = Depends(get_db)
):
    """
    List generated documents with filtering and pagination.
    
    Requires: LAWYER, ASSISTANT, or ADMIN role
    Tenant isolation: Only returns documents from user's firm
    """
    try:
        # Convert string filters to enums if provided
        status_enum = DraftStatus(status_filter) if status_filter else None
        type_enum = LegalDocumentType(document_type) if document_type else None
        
        service = DocumentDraftingService()
        documents = service.list_documents(
            firm_id=current_user.firm_id,
            db=db,
            status=status_enum,
            document_type=type_enum,
            expediente_id=expediente_id,
            limit=limit,
            offset=offset
        )
        
        return [
            GeneratedDocumentResponse(
                **{k: v for k, v in doc.__dict__.items() if not k.startswith('_')},
                created_at=doc.created_at.isoformat(),
                updated_at=doc.updated_at.isoformat(),
                reviewed_at=doc.reviewed_at.isoformat() if doc.reviewed_at else None,
                approved_at=doc.approved_at.isoformat() if doc.approved_at else None
            )
            for doc in documents
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/documents/{document_id}", response_model=GeneratedDocumentResponse)
def get_generated_document(
    document_id: int,
    current_user: User = Depends(require_role(["lawyer", "assistant", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Get a generated document by ID.
    
    Requires: LAWYER, ASSISTANT, or ADMIN role
    Tenant isolation: Only returns documents from user's firm
    """
    try:
        service = DocumentDraftingService()
        doc = service.get_document(
            document_id=document_id,
            firm_id=current_user.firm_id,
            db=db
        )
        
        return GeneratedDocumentResponse(
            **{k: v for k, v in doc.__dict__.items() if not k.startswith('_')},
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
            reviewed_at=doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            approved_at=doc.approved_at.isoformat() if doc.approved_at else None
        )
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


@router.patch("/documents/{document_id}/status", response_model=GeneratedDocumentResponse)
def update_document_status(
    document_id: int,
    request: UpdateStatusRequest,
    current_user: User = Depends(require_role(["lawyer", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Update the status of a generated document (review workflow).
    
    Requires: LAWYER or ADMIN role
    Workflow: draft -> reviewed -> approved
    """
    try:
        # Convert string to enum
        try:
            new_status = DraftStatus(request.status.lower())
        except ValueError:
            raise ValueError(f"Invalid status: {request.status}")
        
        service = DocumentDraftingService()
        doc = service.update_document_status(
            document_id=document_id,
            new_status=new_status,
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            db=db,
            review_notes=request.review_notes
        )
        
        return GeneratedDocumentResponse(
            **{k: v for k, v in doc.__dict__.items() if not k.startswith('_')},
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
            reviewed_at=doc.reviewed_at.isoformat() if doc.reviewed_at else None,
            approved_at=doc.approved_at.isoformat() if doc.approved_at else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== Templates CRUD ====================

@router.post("/templates", response_model=TemplateResponse)
def create_template(
    template: TemplateCreate,
    current_user: User = Depends(require_role(["lawyer", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Create a new document template.
    
    Requires: LAWYER or ADMIN role
    """
    try:
        # Convert string to enum
        try:
            template_type = LegalDocumentType(template.template_type.lower())
        except ValueError:
            raise ValueError(f"Invalid template type: {template.template_type}")
        
        new_template = DocumentTemplate(
            firm_id=current_user.firm_id,
            template_type=template_type,
            name=template.name,
            description=template.description,
            template_content=template.template_content,
            placeholders=template.placeholders,
            is_default=False,  # User-created templates are not default
            is_active=True,
            created_by=current_user.id
        )
        
        db.add(new_template)
        db.commit()
        db.refresh(new_template)
        
        return TemplateResponse(
            **{k: v for k, v in new_template.__dict__.items() if not k.startswith('_')},
            created_at=new_template.created_at.isoformat(),
            updated_at=new_template.updated_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/templates", response_model=List[TemplateResponse])
def list_templates(
    template_type: Optional[str] = None,
    is_active: bool = True,
    current_user: User = Depends(require_role(["lawyer", "assistant", "admin"])),
    db: Session = Depends(get_db)
):
    """
    List document templates.
    
    Requires: LAWYER, ASSISTANT, or ADMIN role
    Tenant isolation: Returns firm templates + default templates
    """
    try:
        query = db.query(DocumentTemplate).filter(
            (DocumentTemplate.firm_id == current_user.firm_id) | (DocumentTemplate.is_default == True),
            DocumentTemplate.is_active == is_active
        )
        
        if template_type:
            try:
                type_enum = LegalDocumentType(template_type.lower())
                query = query.filter(DocumentTemplate.template_type == type_enum)
            except ValueError:
                raise ValueError(f"Invalid template type: {template_type}")
        
        templates = query.order_by(DocumentTemplate.created_at.desc()).all()
        
        return [
            TemplateResponse(
                **{k: v for k, v in t.__dict__.items() if not k.startswith('_')},
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat()
            )
            for t in templates
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    current_user: User = Depends(require_role(["lawyer", "assistant", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Get a template by ID.
    
    Requires: LAWYER, ASSISTANT, or ADMIN role
    Tenant isolation: Access to firm templates + default templates
    """
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.id == template_id,
        (DocumentTemplate.firm_id == current_user.firm_id) | (DocumentTemplate.is_default == True)
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found or not accessible"
        )
    
    return TemplateResponse(
        **{k: v for k, v in template.__dict__.items() if not k.startswith('_')},
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    updates: TemplateUpdate,
    current_user: User = Depends(require_role(["lawyer", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Update a template.
    
    Requires: LAWYER or ADMIN role
    Tenant isolation: Can only update firm's own templates (not default ones)
    """
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.id == template_id,
        DocumentTemplate.firm_id == current_user.firm_id,
        DocumentTemplate.is_default == False  # Cannot update default templates
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found or not editable"
        )
    
    # Apply updates
    if updates.name is not None:
        template.name = updates.name  # type: ignore
    if updates.description is not None:
        template.description = updates.description  # type: ignore
    if updates.template_content is not None:
        template.template_content = updates.template_content  # type: ignore
    if updates.placeholders is not None:
        template.placeholders = updates.placeholders  # type: ignore
    if updates.is_active is not None:
        template.is_active = updates.is_active  # type: ignore
    
    db.commit()
    db.refresh(template)
    
    return TemplateResponse(
        **{k: v for k, v in template.__dict__.items() if not k.startswith('_')},
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Delete a template (soft delete by marking inactive).
    
    Requires: ADMIN role
    Tenant isolation: Can only delete firm's own templates (not default ones)
    """
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.id == template_id,
        DocumentTemplate.firm_id == current_user.firm_id,
        DocumentTemplate.is_default == False  # Cannot delete default templates
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found or not deletable"
        )
    
    # Soft delete
    template.is_active = False  # type: ignore
    db.commit()
    
    return None
