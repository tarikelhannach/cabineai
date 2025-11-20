from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from ..database import get_db
from ..models import User, UserRole
from ..auth.jwt import get_current_user, require_role
from ..auth.auth import get_password_hash

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    
    class Config:
        from_attributes = True

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Obtener perfil del usuario actual"""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value
    }

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar perfil del usuario actual"""
    user = db.query(User).filter(User.id == current_user.id).first()
    
    # Update fields if provided
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        # Check if email is already in use by another user
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está en uso"
            )
        user.email = user_data.email
    # Users cannot change their own role via this endpoint
    
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value
    }

@router.get("/judges", response_model=List[UserResponse])
async def get_judges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener lista de jueces para asignación de casos"""
    # 🔒 TENANT ISOLATION: Filter by firm_id
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )
        
    judges = db.query(User).filter(
        User.role == UserRole.JUDGE,
        User.firm_id == current_user.firm_id  # ← CRITICAL: Only show judges in same firm
    ).all()
    return [
        {
            "id": judge.id,
            "name": judge.name,
            "email": judge.email,
            "role": judge.role.value
        }
        for judge in judges
    ]

@router.get("/", response_model=List[UserResponse])
async def get_users(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.CLERK])),
    db: Session = Depends(get_db)
):
    """Obtener lista de todos los usuarios (solo admin/clerk)"""
    # 🔒 TENANT ISOLATION: Filter by firm_id
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )

    users = db.query(User).filter(User.firm_id == current_user.firm_id).all()  # ← CRITICAL
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role.value
        }
        for user in users
    ]

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.CLERK])),
    db: Session = Depends(get_db)
):
    """Crear nuevo usuario (solo admin/clerk)"""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        firm_id=current_user.firm_id  # ← CRITICAL: Assign to same firm
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role.value
    }

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.CLERK])),
    db: Session = Depends(get_db)
):
    """Actualizar usuario (solo admin/clerk)"""
    # 🔒 TENANT ISOLATION: Filter by firm_id
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )

    user = db.query(User).filter(
        User.id == user_id,
        User.firm_id == current_user.firm_id  # ← CRITICAL: Prevent cross-tenant update
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Update fields if provided
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        # Check if email is already in use by another user
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está en uso"
            )
        user.email = user_data.email
    if user_data.role is not None:
        user.role = user_data.role
    
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value
    }

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Eliminar usuario (solo admin)"""
    # 🔒 TENANT ISOLATION: Filter by firm_id
    if not current_user.firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any firm"
        )

    user = db.query(User).filter(
        User.id == user_id,
        User.firm_id == current_user.firm_id  # ← CRITICAL: Prevent cross-tenant deletion
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario"
        )
    
    db.delete(user)
    db.commit()
    
    return None
