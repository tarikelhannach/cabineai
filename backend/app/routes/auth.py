from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..database import get_db
from ..models import User, UserRole, AuditLog
from ..auth.jwt import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from ..auth.two_factor import TwoFactorAuth
from ..auth.utils import (
    generate_password_reset_token,
    verify_password_reset_token,
    invalidate_password_reset_token
)
from ..config import settings
from ..middleware.rate_limit import ip_limiter
from ..services.notification_service import NotificationService

router = APIRouter(prefix="/auth", tags=["authentication"])
twofa = TwoFactorAuth()
notification_service = NotificationService()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    password: str
    role: UserRole = UserRole.LAWYER
    firm_name: str

class InviteRequest(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.LAWYER

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    is_verified: bool
    
    class Config:
        from_attributes = True

@router.post("/login", response_model=TokenResponse)
@ip_limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
async def login(request: Request, response: Response, login_data: LoginRequest, db: Session = Depends(get_db)):
    """Iniciar sesión con rate limiting (5 intentos/minuto por IP)"""
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        # Log failed login attempt
        audit_log = AuditLog(
            action="login_failed",
            resource_type="auth",
            details=f"Failed login attempt for {login_data.email}",
            status="failed"
        )
        db.add(audit_log)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},  # Include user_id for middleware
        expires_delta=access_token_expires
    )
    
    # Log successful login
    audit_log = AuditLog(
        user_id=user.id,
        action="login",
        resource_type="auth",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified
        }
    }

@router.post("/register", response_model=TokenResponse)
@ip_limiter.limit("3/hour")
async def register(request: Request, response: Response, register_data: RegisterRequest, db: Session = Depends(get_db)):
    """Registrar nueva firma y usuario administrador"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == register_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Create Firm
    from ..models import Firm, SubscriptionStatus, SubscriptionTier
    new_firm = Firm(
        name=register_data.firm_name,
        email=register_data.email,  # Contact email
        subscription_status=SubscriptionStatus.TRIAL,
        subscription_tier=SubscriptionTier.BASIC
    )
    db.add(new_firm)
    db.commit()
    db.refresh(new_firm)
    
    # Create Admin User
    new_user = User(
        email=register_data.email,
        name=register_data.name,
        hashed_password=get_password_hash(register_data.password[:72]),
        role=UserRole.ADMIN,
        firm_id=new_firm.id,
        is_active=True,
        is_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": new_user.id},  # Include user_id for middleware
        expires_delta=access_token_expires
    )
    
    # Log registration
    audit_log = AuditLog(
        user_id=new_user.id,
        firm_id=new_firm.id,
        action="firm_registered",
        resource_type="firm",
        resource_id=new_firm.id,
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "role": new_user.role.value,
            "is_active": new_user.is_active,
            "is_verified": new_user.is_verified
        }
    }

@router.post("/invite")
async def invite_user(
    invite_data: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invitar usuario a la firma (Solo Admin)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores pueden invitar")
        
    # Check limits
    firm = db.query(Firm).filter(Firm.id == current_user.firm_id).first()
    current_users_count = db.query(User).filter(User.firm_id == firm.id).count()
    
    if current_users_count >= firm.max_users:
        raise HTTPException(status_code=400, detail="Límite de usuarios alcanzado")
        
    # Create user (placeholder password)
    import secrets
    temp_password = secrets.token_urlsafe(10)
    
    new_user = User(
        email=invite_data.email,
        name=invite_data.email.split('@')[0],
        hashed_password=get_password_hash(temp_password),
        role=invite_data.role,
        firm_id=firm.id,
        is_active=True,
        is_verified=True # Invited users are trusted
    )
    
    db.add(new_user)
    db.commit()
    
    # Send invitation email
    email_sent = await notification_service.send_user_invitation(
        email=invite_data.email,
        password=temp_password,
        language="fr" # Default to French for business context, or could be passed in request
    )
    
    # Log the invitation for audit purposes
    audit_log = AuditLog(
        user_id=current_user.id,
        firm_id=firm.id,
        action="user_invited",
        resource_type="user",
        resource_id=new_user.id,
        details=f"Invited user {invite_data.email}. Email sent: {email_sent}",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"User invitation created for {invite_data.email} by user {current_user.email}")
    
    if not email_sent:
        return {
            "message": "Usuario creado, pero falló el envío del email. Por favor contacte al soporte.",
            "warning": "Email delivery failed"
        }
    
    return {"message": "Usuario invitado exitosamente. La contraseña temporal ha sido enviada por email."}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Obtener información del usuario actual"""
    return current_user

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cerrar sesión (registrar en audit log)"""
    audit_log = AuditLog(
        user_id=current_user.id,
        action="logout",
        resource_type="auth",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Sesión cerrada exitosamente"}

class Enable2FAResponse(BaseModel):
    secret: str
    qr_code: str
    message: str

class Verify2FARequest(BaseModel):
    code: str

class LoginWith2FARequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Generar QR code para activar 2FA"""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA ya está activado"
        )
    
    secret = twofa.generate_secret_key(current_user.email)
    qr_code = twofa.generate_qr_code(current_user.email, secret)
    
    current_user.totp_secret = secret
    db.commit()
    
    audit_log = AuditLog(
        user_id=current_user.id,
        action="2fa_setup_initiated",
        resource_type="auth",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "secret": secret,
        "qr_code": qr_code,
        "message": "Escanea el código QR con tu app de autenticación"
    }

@router.post("/2fa/verify")
async def verify_2fa(
    request_data: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verificar código TOTP y activar 2FA"""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes iniciar la configuración de 2FA"
        )
    
    is_valid = twofa.verify_totp_code(
        current_user.totp_secret,
        request_data.code,
        current_user.email
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código TOTP inválido"
        )
    
    current_user.totp_enabled = True
    db.commit()
    
    audit_log = AuditLog(
        user_id=current_user.id,
        action="2fa_enabled",
        resource_type="auth",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "2FA activado exitosamente"}

@router.post("/2fa/disable")
async def disable_2fa(
    request_data: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Desactivar 2FA con verificación de código"""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA no está activado"
        )
    
    is_valid = twofa.verify_totp_code(
        current_user.totp_secret,
        request_data.code,
        current_user.email
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código TOTP inválido"
        )
    
    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.commit()
    
    audit_log = AuditLog(
        user_id=current_user.id,
        action="2fa_disabled",
        resource_type="auth",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "2FA desactivado exitosamente"}

@router.post("/login-2fa", response_model=TokenResponse)
@ip_limiter.limit("5/minute")
async def login_with_2fa(
    request: Request,
    response: Response,
    login_data: LoginWith2FARequest,
    db: Session = Depends(get_db)
):
    """Login con soporte para 2FA"""
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        audit_log = AuditLog(
            action="login_failed",
            resource_type="auth",
            details=f"Failed login attempt for {login_data.email}",
            status="failed"
        )
        db.add(audit_log)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado"
        )
    
    if user.totp_enabled:
        if not login_data.totp_code:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="Se requiere código 2FA",
                headers={"X-2FA-Required": "true"}
            )
        
        is_valid = twofa.verify_totp_code(
            user.totp_secret,
            login_data.totp_code,
            user.email
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Código 2FA inválido"
            )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},  # Include user_id for middleware
        expires_delta=access_token_expires
    )
    
    audit_log = AuditLog(
        user_id=user.id,
        action="login",
        resource_type="auth",
        details="Login with 2FA" if user.totp_enabled else "Login without 2FA",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified
        }
    }

@router.post("/password/reset-request")
@ip_limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    response: Response,
    reset_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Solicitar reset de contraseña"""
    user = db.query(User).filter(User.email == reset_data.email).first()
    
    if not user:
        return {"message": "Si el email existe, recibirás instrucciones"}
    
    token = generate_password_reset_token(user.email)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al generar token de reset"
        )
    
    audit_log = AuditLog(
        user_id=user.id,
        action="password_reset_requested",
        resource_type="auth",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "message": "Si el email existe, recibirás instrucciones",
        "token": token
    }

@router.post("/password/reset-confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirmar reset de contraseña con token"""
    email = verify_password_reset_token(reset_data.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    user.hashed_password = get_password_hash(reset_data.new_password[:72])
    db.commit()
    
    invalidate_password_reset_token(reset_data.token)
    
    audit_log = AuditLog(
        user_id=user.id,
        action="password_reset_completed",
        resource_type="auth",
        status="success"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Contraseña actualizada exitosamente"}
