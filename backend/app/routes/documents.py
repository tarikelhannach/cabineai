from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import io
import shutil
from pathlib import Path
import uuid

from ..database import get_db
from ..models import Document as DocumentModel, User, Expediente, Firm
from ..auth.jwt import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/documents", tags=["documents"])

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    case_id: Optional[int]
    uploaded_by: int
    ocr_processed: bool
    is_signed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    message: str

class UpdateOCRRequest(BaseModel):
    ocr_text: str

UPLOAD_DIR = Path("/tmp/judicial_documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

MAX_FILE_SIZE = 50 * 1024 * 1024

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    case_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔒 MULTI-TENANT SECURITY: Validate firm access
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )
    
    # 💳 SUBSCRIPTION VALIDATION: Check active subscription
    firm = db.query(Firm).filter(Firm.id == current_user.firm_id).first()
    if not firm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Firm not found"
        )
    
    if firm.subscription_status != "active":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription expired. Please renew to upload documents."
        )
    
    # 🔒 TENANT ISOLATION: Validate case belongs to same firm
    if case_id:
        case = db.query(Expediente).filter(
            Expediente.id == case_id,
            Expediente.firm_id == current_user.firm_id  # ← CRITICAL: Prevent cross-tenant access
        ).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expediente not found or access denied"
            )
        
        # RBAC: Check permissions
        if current_user.role.value not in ["admin", "lawyer"]:
            if case.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to upload documents to this expediente"
                )
    
    if not file.content_type in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido. Tipos aceptados: {', '.join(ALLOWED_MIME_TYPES)}"
        )
    
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archivo demasiado grande. Tamaño máximo: {MAX_FILE_SIZE / (1024*1024)}MB"
        )
    
    file_path = None
    try:
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        user_dir = UPLOAD_DIR / str(current_user.id)
        user_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = user_dir / unique_filename
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        new_document = DocumentModel(
            firm_id=current_user.firm_id,  # ← CRITICAL: Always set firm_id
            filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=file.content_type,
            case_id=case_id,
            uploaded_by=current_user.id
        )
        
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        try:
            from app.tasks.ocr_tasks import process_document_ocr, index_document_elasticsearch
            from celery import chord
            
            workflow = chord([process_document_ocr.s(new_document.id)], 
                           index_document_elasticsearch.s())
            result = workflow.apply_async()
            
            message = f"Documento subido exitosamente. OCR en proceso (task_id: {result.id})"
        except Exception as e:
            message = f"Documento subido exitosamente. OCR no disponible: {str(e)}"
        
        return DocumentUploadResponse(
            id=new_document.id,
            filename=new_document.filename,
            file_path=new_document.file_path,
            message=message
        )
    
    except Exception as e:
        db.rollback()
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir documento: {str(e)}"
        )

@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔒 TENANT ISOLATION: Filter by firm_id
    document = db.query(DocumentModel).filter(
        DocumentModel.id == document_id,
        DocumentModel.firm_id == current_user.firm_id  # ← CRITICAL
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    # RBAC: Check permissions
    if current_user.role.value not in ["admin", "lawyer"]:
        if document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this document"
            )
    
    try:
        file_path = Path(document.file_path)
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado en el servidor"
            )
        
        return FileResponse(
            path=str(file_path),
            media_type=document.mime_type or "application/octet-stream",
            filename=document.filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al descargar documento: {str(e)}"
        )

@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    case_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔒 TENANT ISOLATION: Always filter by firm_id
    query = db.query(DocumentModel).filter(
        DocumentModel.firm_id == current_user.firm_id  # ← CRITICAL
    )
    
    if case_id:
        # Validate case belongs to same firm
        case = db.query(Expediente).filter(
            Expediente.id == case_id,
            Expediente.firm_id == current_user.firm_id  # ← CRITICAL
        ).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expediente not found or access denied"
            )
        
        query = query.filter(DocumentModel.case_id == case_id)
    else:
        if current_user.role.value not in ["admin", "clerk"]:
            query = query.filter(DocumentModel.uploaded_by == current_user.id)
    
    documents = query.offset(skip).limit(limit).all()
    return documents

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if document.case_id:
        case = db.query(Case).filter(Case.id == document.case_id).first()
        if current_user.role.value not in ["admin", "clerk"]:
            if current_user.role.value == "judge":
                if case.assigned_judge_id != current_user.id:
                    raise HTTPException(status_code=403, detail="No autorizado")
            elif case.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="No autorizado")
    
    elif document.uploaded_by != current_user.id and current_user.role.value not in ["admin", "clerk"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    return document

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.core.cache import get_cache_manager
    cache = get_cache_manager()
    
    document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if current_user.role.value not in ["admin", "clerk"]:
        if document.case_id:
            case = db.query(Case).filter(Case.id == document.case_id).first()
            if not case:
                raise HTTPException(status_code=404, detail="Caso asociado no encontrado")
            
            if current_user.role.value == "judge":
                if case.assigned_judge_id != current_user.id:
                    raise HTTPException(status_code=403, detail="No autorizado para eliminar este documento")
            elif case.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="No autorizado para eliminar este documento")
        elif document.uploaded_by != current_user.id:
            raise HTTPException(status_code=403, detail="No autorizado para eliminar este documento")
    
    try:
        case_id = document.case_id
        
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
        
        db.delete(document)
        db.commit()
        
        await cache.invalidate_document(document_id, case_id)
        
        return {"message": "Documento eliminado exitosamente"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar documento: {str(e)}"
        )

@router.post("/{document_id}/process-ocr")
async def process_document_ocr_sync(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Procesar OCR para un documento de forma síncrona.
    Endpoint útil para testing y procesamiento inmediato de documentos pequeños.
    """
    from app.services.ocr_service import SyncOCRService
    
    document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if document.case_id:
        case = db.query(Case).filter(Case.id == document.case_id).first()
        if current_user.role.value not in ["admin", "clerk"]:
            if current_user.role.value == "judge":
                if case.assigned_judge_id != current_user.id:
                    raise HTTPException(status_code=403, detail="No autorizado")
            elif case.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="No autorizado")
    elif document.uploaded_by != current_user.id and current_user.role.value not in ["admin", "clerk"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    if document.ocr_processed:
        return {
            "message": "Documento ya procesado con OCR",
            "ocr_text": document.ocr_text,
            "ocr_confidence": document.ocr_confidence,
            "ocr_language": document.ocr_language
        }
    
    try:
        from app.services.elasticsearch_service import get_elasticsearch_service
        
        ocr_service = SyncOCRService()
        result = ocr_service.process_document(document.file_path)
        
        document.ocr_processed = True
        document.ocr_text = result['extracted_text']
        document.ocr_confidence = result['ocr_confidence']
        document.ocr_language = result['detected_language']
        document.is_searchable = True
        
        db.commit()
        db.refresh(document)
        
        # Indexar en Elasticsearch
        try:
            es_service = get_elasticsearch_service()
            es_service.index_document({
                'document_id': document.id,
                'filename': document.filename,
                'ocr_text': document.ocr_text,
                'ocr_language': document.ocr_language,
                'ocr_confidence': document.ocr_confidence,
                'case_id': document.case_id,
                'uploaded_by': document.uploaded_by,
                'is_searchable': True
            })
        except Exception as es_error:
            # No fallar si Elasticsearch no está disponible
            pass
        
        return {
            "message": "OCR procesado exitosamente",
            "ocr_text": result['extracted_text'],
            "ocr_confidence": result['ocr_confidence'],
            "ocr_language": result['detected_language'],
            "processing_time": result['processing_time'],
            "pages_processed": result['pages_processed']
        }
    
    except Exception as e:
            detail=f"Error al procesar OCR: {str(e)}"
        )

@router.put("/{document_id}/ocr")
async def update_document_ocr(
    document_id: int,
    request: UpdateOCRRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update OCR text for a document (Human-in-the-loop verification).
    Marks the document as verified.
    """
    # 🔒 TENANT ISOLATION: Filter by firm_id
    document = db.query(DocumentModel).filter(
        DocumentModel.id == document_id,
        DocumentModel.firm_id == current_user.firm_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    # RBAC: Check permissions (only lawyers/admins/assistants can verify)
    if current_user.role.value not in ["admin", "lawyer", "assistant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to verify documents"
        )
    
    try:
        # Update OCR text
        document.ocr_text = request.ocr_text
        document.is_verified = True
        document.verified_at = datetime.utcnow()
        
        # Re-index in Elasticsearch if available
        try:
            from app.services.elasticsearch_service import get_elasticsearch_service
            es_service = get_elasticsearch_service()
            es_service.index_document({
                'document_id': document.id,
                'filename': document.filename,
                'ocr_text': document.ocr_text,
                'ocr_language': document.ocr_language,
                'ocr_confidence': document.ocr_confidence,
                'case_id': document.case_id,
                'uploaded_by': document.uploaded_by,
                'is_searchable': True
            })
        except Exception:
            # Ignore ES errors during update
            pass
            
        db.commit()
        db.refresh(document)
        
        return {
            "message": "OCR updated and verified successfully",
            "id": document.id,
            "is_verified": True
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating OCR: {str(e)}"
        )
