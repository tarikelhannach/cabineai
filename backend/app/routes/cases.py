from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Case, User, UserRole, CaseStatus, AuditLog
from ..auth.jwt import get_current_user, require_role

router = APIRouter(prefix="/cases", tags=["cases"])

class CaseCreate(BaseModel):
    expediente_number: str
    client_name: str
    description: Optional[str] = None
    status: CaseStatus = CaseStatus.PENDING
    assigned_lawyer_id: Optional[int] = None

class CaseUpdate(BaseModel):
    client_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    assigned_lawyer_id: Optional[int] = None

class CaseResponse(BaseModel):
    id: int
    expediente_number: str
    client_name: str
    description: Optional[str]
    status: str
    owner_id: int
    assigned_lawyer_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    owner: dict
    assigned_lawyer: Optional[dict] = None
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[CaseResponse])
async def get_cases(
    skip: int = 0,
    limit: int = 100,
    status: Optional[CaseStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener lista de casos"""
    # 🔒 TENANT ISOLATION: Always filter by firm_id FIRST
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )
    
    query = db.query(Case).filter(Case.firm_id == current_user.firm_id)  # ← CRITICAL
    
    # Filter based on user role (within same firm)
    if current_user.role == UserRole.LAWYER:
        query = query.filter(Case.owner_id == current_user.id)
    elif current_user.role == UserRole.JUDGE:
        query = query.filter(Case.assigned_lawyer_id == current_user.id)
    elif current_user.role == UserRole.CLERK:
        pass  # Clerk can see all cases in their firm
    elif current_user.role == UserRole.ADMIN:
        pass  # Admin can see all cases in their firm
    else:
        query = query.filter(Case.owner_id == current_user.id)
    
    # Filter by status if provided
    if status:
        query = query.filter(Case.status == status)
    
    cases = query.offset(skip).limit(limit).all()
    
    # Format response
    result = []
    for case in cases:
        case_dict = {
            "id": case.id,
            "expediente_number": case.expediente_number,
            "client_name": case.client_name,
            "description": case.description,
            "status": case.status.value,
            "owner_id": case.owner_id,
            "assigned_lawyer_id": case.assigned_lawyer_id,
            "created_at": case.created_at,
            "updated_at": case.updated_at,
            "owner": {
                "id": case.owner.id,
                "name": case.owner.name,
                "email": case.owner.email,
                "role": case.owner.role.value
            },
            "assigned_lawyer": {
                "id": case.assigned_lawyer.id,
                "name": case.assigned_lawyer.name,
                "email": case.assigned_lawyer.email,
                "role": case.assigned_lawyer.role.value
            } if case.assigned_lawyer else None
        }
        result.append(case_dict)
    
    return result

@router.get("/search/", response_model=List[CaseResponse])
async def search_cases(
    query: Optional[str] = None,
    status: Optional[CaseStatus] = None,
    assigned_lawyer_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Buscar casos con filtros avanzados"""
    # 🔒 TENANT ISOLATION: Always filter by firm_id FIRST
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )
    
    # Start with base query filtered by firm
    base_query = db.query(Case).filter(Case.firm_id == current_user.firm_id)  # ← CRITICAL
    
    # Apply role-based filtering (same as get_cases, within same firm)
    if current_user.role == UserRole.LAWYER:
        base_query = base_query.filter(Case.owner_id == current_user.id)
    elif current_user.role == UserRole.JUDGE:
        base_query = base_query.filter(Case.assigned_lawyer_id == current_user.id)
    elif current_user.role == UserRole.CLERK:
        pass  # Clerk can see all cases in their firm
    elif current_user.role == UserRole.ADMIN:
        pass  # Admin can see all cases in their firm
    else:
        base_query = base_query.filter(Case.owner_id == current_user.id)
    
    # Apply search filters
    if query:
        search_filter = (
            Case.expediente_number.ilike(f"%{query}%") |
            Case.client_name.ilike(f"%{query}%") |
            Case.description.ilike(f"%{query}%")
        )
        base_query = base_query.filter(search_filter)
    
    if status:
        base_query = base_query.filter(Case.status == status)
    
    if assigned_lawyer_id:
        base_query = base_query.filter(Case.assigned_lawyer_id == assigned_lawyer_id)
    
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date)
            base_query = base_query.filter(Case.created_at >= start_datetime)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date)
            base_query = base_query.filter(Case.created_at <= end_datetime)
        except ValueError:
            pass
    
    # Execute query with pagination
    cases = base_query.offset(skip).limit(limit).all()
    
    # Format response
    result = []
    for case in cases:
        case_dict = {
            "id": case.id,
            "expediente_number": case.expediente_number,
            "client_name": case.client_name,
            "description": case.description,
            "status": case.status.value,
            "owner_id": case.owner_id,
            "assigned_lawyer_id": case.assigned_lawyer_id,
            "created_at": case.created_at,
            "updated_at": case.updated_at,
            "owner": {
                "id": case.owner.id,
                "name": case.owner.name,
                "email": case.owner.email,
                "role": case.owner.role.value
            },
            "assigned_lawyer": {
                "id": case.assigned_lawyer.id,
                "name": case.assigned_lawyer.name,
                "email": case.assigned_lawyer.email,
                "role": case.assigned_lawyer.role.value
            } if case.assigned_lawyer else None
        }
        result.append(case_dict)
    
    return result

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener detalles de un caso específico"""
    # 🔒 TENANT ISOLATION: Filter by firm_id FIRST
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )
    
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.firm_id == current_user.firm_id  # ← CRITICAL: Prevent cross-tenant access
    ).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )
    
    # Check permissions based on role with deny-by-default (within same firm)
    if current_user.role == UserRole.ADMIN or current_user.role == UserRole.CLERK:
        # Admin and clerk can view all cases in their firm
        pass
    elif current_user.role == UserRole.LAWYER:
        # Lawyers can only view their own cases
        if case.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver este caso"
            )
    elif current_user.role == UserRole.JUDGE:
        # Judges can only view cases assigned to them
        if case.assigned_lawyer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver este caso"
            )
    elif current_user.role == UserRole.CITIZEN:
        # Citizens can only view cases they own
        if case.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver este caso"
            )
    else:
        # Unknown role - deny by default
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol de usuario no autorizado"
        )
    
    return {
        "id": case.id,
        "expediente_number": case.expediente_number,
        "client_name": case.client_name,
        "description": case.description,
        "status": case.status.value,
        "owner_id": case.owner_id,
        "assigned_lawyer_id": case.assigned_lawyer_id,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "owner": {
            "id": case.owner.id,
            "name": case.owner.name,
            "email": case.owner.email,
            "role": case.owner.role.value
        },
        "assigned_lawyer": {
            "id": case.assigned_lawyer.id,
            "name": case.assigned_lawyer.name,
            "email": case.assigned_lawyer.email,
            "role": case.assigned_lawyer.role.value
        } if case.assigned_lawyer else None
    }

@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crear un nuevo caso"""
    # 🔒 TENANT ISOLATION: Ensure user belongs to a firm
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )
    
    # Check if case number already exists (within same firm)
    existing_case = db.query(Case).filter(
        Case.expediente_number == case_data.expediente_number,
        Case.firm_id == current_user.firm_id  # ← CRITICAL: Case numbers unique per firm
    ).first()
    if existing_case:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El número de caso ya existe"
        )
    
    # Determine if user can set sensitive fields during creation
    can_set_sensitive_fields = (
        current_user.role == UserRole.ADMIN or 
        current_user.role == UserRole.CLERK or 
        current_user.role == UserRole.JUDGE
    )
    
    # Prevent citizens and lawyers from setting sensitive fields
    if not can_set_sensitive_fields:
        if case_data.status != CaseStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para establecer el estado del caso"
            )
        if case_data.assigned_lawyer_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para asignar un juez al caso"
            )
    
    # Validate assigned judge if provided
    assigned_lawyer_id = None
    if case_data.assigned_lawyer_id is not None:
        if can_set_sensitive_fields:
            judge = db.query(User).filter(
                User.id == case_data.assigned_lawyer_id,
                User.role == UserRole.JUDGE
            ).first()
            if not judge:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El juez asignado no existe o no tiene el rol correcto"
                )
            assigned_lawyer_id = case_data.assigned_lawyer_id
    
    # Create new case with validated data
    new_case = Case(
        firm_id=current_user.firm_id,  # ← CRITICAL: Always set firm_id
        expediente_number=case_data.expediente_number,
        client_name=case_data.client_name,
        description=case_data.description,
        status=case_data.status if can_set_sensitive_fields else CaseStatus.PENDING,
        owner_id=current_user.id,
        assigned_lawyer_id=assigned_lawyer_id
    )
    
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    
    # Log case creation
    audit_log = AuditLog(
        user_id=current_user.id,
        action="create_case",
        resource_type="case",
        resource_id=new_case.id,
        details=f"Created case {new_case.expediente_number}",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "id": new_case.id,
        "expediente_number": new_case.expediente_number,
        "client_name": new_case.client_name,
        "description": new_case.description,
        "status": new_case.status.value,
        "owner_id": new_case.owner_id,
        "assigned_lawyer_id": new_case.assigned_lawyer_id,
        "created_at": new_case.created_at,
        "updated_at": new_case.updated_at,
        "owner": {
            "id": new_case.owner.id,
            "name": new_case.owner.name,
            "email": new_case.owner.email,
            "role": new_case.owner.role.value
        },
        "assigned_lawyer": {
            "id": new_case.assigned_lawyer.id,
            "name": new_case.assigned_lawyer.name,
            "email": new_case.assigned_lawyer.email,
            "role": new_case.assigned_lawyer.role.value
        } if new_case.assigned_lawyer else None
    }

@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: int,
    case_data: CaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar un caso existente"""
    from app.core.cache import get_cache_manager
    cache = get_cache_manager()
    
    # 🔒 TENANT ISOLATION: Filter by firm_id FIRST
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )
    
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.firm_id == current_user.firm_id  # ← CRITICAL: Prevent cross-tenant access
    ).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )
    
    # Determine allowed fields and access based on role (within same firm)
    can_update_sensitive_fields = False
    can_access_case = False
    
    if current_user.role == UserRole.ADMIN or current_user.role == UserRole.CLERK:
        # Admin and clerk can update all cases and all fields in their firm
        can_access_case = True
        can_update_sensitive_fields = True
    elif current_user.role == UserRole.JUDGE:
        # Judges can update cases assigned to them, including status
        if case.assigned_lawyer_id == current_user.id:
            can_access_case = True
            can_update_sensitive_fields = True
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar este caso"
            )
    elif current_user.role == UserRole.LAWYER:
        # Lawyers can only update their own cases, limited fields
        if case.owner_id == current_user.id:
            can_access_case = True
            can_update_sensitive_fields = False
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar este caso"
            )
    elif current_user.role == UserRole.CITIZEN:
        # Citizens can only update their own cases, very limited fields
        if case.owner_id == current_user.id:
            can_access_case = True
            can_update_sensitive_fields = False
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar este caso"
            )
    else:
        # Unknown role - deny by default
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol de usuario no autorizado"
        )
    
    if not can_access_case:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este caso"
        )
    
    # Check if trying to update sensitive fields without permission
    if not can_update_sensitive_fields:
        if case_data.status is not None or case_data.assigned_lawyer_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar el estado o asignación del caso"
            )
    
    # Update allowed fields
    if case_data.client_name is not None:
        case.client_name = case_data.client_name
    if case_data.description is not None:
        case.description = case_data.description
    
    # Update sensitive fields only if authorized
    if can_update_sensitive_fields:
        if case_data.status is not None:
            case.status = case_data.status
        if case_data.assigned_lawyer_id is not None:
            # Verify the assigned judge exists and is actually a judge
            if case_data.assigned_lawyer_id:
                judge = db.query(User).filter(
                    User.id == case_data.assigned_lawyer_id,
                    User.role == UserRole.JUDGE
                ).first()
                if not judge:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="El juez asignado no existe o no tiene el rol correcto"
                    )
            case.assigned_lawyer_id = case_data.assigned_lawyer_id
    
    db.commit()
    db.refresh(case)
    
    await cache.invalidate_case(case_id)
    
    # Log case update
    audit_log = AuditLog(
        user_id=current_user.id,
        action="update_case",
        resource_type="case",
        resource_id=case.id,
        details=f"Updated case {case.expediente_number}",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "id": case.id,
        "expediente_number": case.expediente_number,
        "client_name": case.client_name,
        "description": case.description,
        "status": case.status.value,
        "owner_id": case.owner_id,
        "assigned_lawyer_id": case.assigned_lawyer_id,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "owner": {
            "id": case.owner.id,
            "name": case.owner.name,
            "email": case.owner.email,
            "role": case.owner.role.value
        },
        "assigned_lawyer": {
            "id": case.assigned_lawyer.id,
            "name": case.assigned_lawyer.name,
            "email": case.assigned_lawyer.email,
            "role": case.assigned_lawyer.role.value
        } if case.assigned_lawyer else None
    }

@router.delete("/{case_id}")
async def delete_case(
    case_id: int,
    current_user: User = Depends(require_role(["admin", "clerk"])),
    db: Session = Depends(get_db)
):
    """Eliminar un caso (solo admin o clerk)"""
    from app.core.cache import get_cache_manager
    cache = get_cache_manager()
    case = db.query(Case).filter(Case.id == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )
    
    # Log case deletion
    audit_log = AuditLog(
        user_id=current_user.id,
        action="delete_case",
        resource_type="case",
        resource_id=case.id,
        details=f"Deleted case {case.expediente_number}",
        status="success"
    )
    db.add(audit_log)
    
    db.delete(case)
    db.commit()
    
    await cache.invalidate_case(case_id)
    
    return {"message": f"Caso {case.expediente_number} eliminado exitosamente"}

@router.get("/stats/summary")
async def get_case_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener estadísticas de casos"""
    query = db.query(Case)
    
    # Filter based on user role
    if current_user.role == UserRole.LAWYER:
        query = query.filter(Case.owner_id == current_user.id)
    elif current_user.role == UserRole.JUDGE:
        query = query.filter(Case.assigned_lawyer_id == current_user.id)
    
    total = query.count()
    pending = query.filter(Case.status == CaseStatus.PENDING).count()
    in_progress = query.filter(Case.status == CaseStatus.IN_PROGRESS).count()
    resolved = query.filter(Case.status == CaseStatus.RESOLVED).count()
    closed = query.filter(Case.status == CaseStatus.CLOSED).count()
    
    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "closed": closed
    }
