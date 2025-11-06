"""
Billing API Routes
Handles firm registration, subscription management, and invoice operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import date

from ..database import get_db
from ..models import (
    Firm, Subscription, Invoice, User, UserRole,
    SubscriptionTier, SubscriptionStatus, InvoiceStatus,
    LanguagePreference
)
from ..services.billing_service import BillingService
from ..auth.jwt import get_current_user
from ..middleware.tenant import get_current_firm_id


# Pydantic Schemas

class FirmRegistrationRequest(BaseModel):
    """Request schema for new firm registration"""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    subscription_tier: SubscriptionTier
    language_preference: LanguagePreference = LanguagePreference.FRENCH
    
    # Admin user details
    admin_name: str = Field(..., min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)


class FirmRegistrationResponse(BaseModel):
    """Response schema for firm registration"""
    firm_id: int
    firm_name: str
    subscription_tier: str
    implementation_fee: float
    monthly_fee_per_lawyer: int
    subscription_status: str
    admin_user_id: int
    message: str


class SubscriptionStatusResponse(BaseModel):
    """Response schema for subscription status"""
    firm_id: int
    firm_name: str
    status: str
    is_active: bool
    tier: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    next_billing_date: Optional[str] = None
    monthly_cost: Optional[float] = None
    message: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Response schema for invoice"""
    id: int
    invoice_number: str
    amount: float
    currency: str
    invoice_date: str
    due_date: str
    status: str
    description: Optional[str] = None
    paid_date: Optional[str] = None


class InvoiceListResponse(BaseModel):
    """Response schema for invoice list"""
    firm_id: int
    firm_name: str
    invoices: List[InvoiceResponse]
    total_invoices: int
    total_amount: float
    pending_amount: float


# Router

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/init", response_model=FirmRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def initialize_firm_registration(
    request: FirmRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Initialize a new firm registration with subscription.
    This is the entry point for new law firms signing up for the SaaS platform.
    
    - Creates firm account
    - Sets up subscription (BASIC or COMPLETE tier)
    - Creates admin user
    - Generates first invoice
    """
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Check if firm email already exists
    existing_firm = db.query(Firm).filter(Firm.email == request.email).first()
    if existing_firm:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A firm with this email already exists"
        )
    
    # Check if admin email already exists
    existing_user = db.query(User).filter(User.email == request.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists"
        )
    
    # Calculate implementation fee based on tier
    implementation_fee = (
        BillingService.IMPLEMENTATION_FEE_COMPLETE 
        if request.subscription_tier == SubscriptionTier.COMPLETE 
        else BillingService.IMPLEMENTATION_FEE_BASIC
    )
    
    # Create firm
    firm = Firm(
        name=request.name,
        email=request.email,
        phone=request.phone,
        address=request.address,
        subscription_tier=request.subscription_tier,
        subscription_status=SubscriptionStatus.TRIAL,  # Start with trial
        language_preference=request.language_preference,
        implementation_fee_paid=False,  # To be paid separately
        monthly_fee_per_lawyer=BillingService.MONTHLY_FEE_PER_LAWYER
    )
    
    db.add(firm)
    db.flush()  # Get firm.id without committing
    
    # Create admin user
    hashed_password = pwd_context.hash(request.admin_password)
    admin_user = User(
        firm_id=firm.id,
        email=request.admin_email,
        name=request.admin_name,
        hashed_password=hashed_password,
        role=UserRole.ADMIN,
        language=request.language_preference,
        is_active=True,
        is_verified=True  # Auto-verify admin on registration
    )
    
    db.add(admin_user)
    db.flush()
    
    # Initialize subscription
    subscription = BillingService.initialize_firm_subscription(
        db=db,
        firm_id=firm.id,
        tier=request.subscription_tier,
        duration_months=36  # 3 years to cover GPU cost
    )
    
    db.commit()
    
    return FirmRegistrationResponse(
        firm_id=firm.id,
        firm_name=firm.name,
        subscription_tier=request.subscription_tier.value,
        implementation_fee=implementation_fee,
        monthly_fee_per_lawyer=BillingService.MONTHLY_FEE_PER_LAWYER,
        subscription_status=subscription.status.value,
        admin_user_id=admin_user.id,
        message=f"Firm registered successfully. Implementation fee: {implementation_fee} MAD. Monthly fee: {BillingService.MONTHLY_FEE_PER_LAWYER} MAD per lawyer."
    )


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current subscription status for the authenticated user's firm.
    
    Returns:
    - Subscription status (active, expired, trial, suspended)
    - Billing dates
    - Monthly cost
    - Tier information
    """
    firm_id = get_current_firm_id(request)
    
    status_info = BillingService.check_subscription_status(db, firm_id)
    
    return SubscriptionStatusResponse(**status_info)


@router.get("/invoice/current", response_model=InvoiceResponse)
async def get_current_invoice(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the most recent invoice for the authenticated user's firm.
    """
    firm_id = get_current_firm_id(request)
    
    # Get the most recent invoice
    invoice = db.query(Invoice).filter(
        Invoice.firm_id == firm_id
    ).order_by(Invoice.invoice_date.desc()).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No invoices found for your firm"
        )
    
    return InvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        amount=invoice.amount,
        currency=invoice.currency,
        invoice_date=invoice.invoice_date.isoformat(),
        due_date=invoice.due_date.isoformat(),
        status=invoice.status.value,
        description=invoice.description,
        paid_date=invoice.paid_date.isoformat() if invoice.paid_date else None
    )


@router.get("/invoices", response_model=InvoiceListResponse)
async def get_all_invoices(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[InvoiceStatus] = None,
    limit: int = 50
):
    """
    Get all invoices for the authenticated user's firm.
    
    Query Parameters:
    - status_filter: Filter by invoice status (pending, paid, overdue, cancelled)
    - limit: Maximum number of invoices to return (default 50)
    """
    firm_id = get_current_firm_id(request)
    
    # Get firm name
    firm = db.query(Firm).filter(Firm.id == firm_id).first()
    if not firm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Firm not found"
        )
    
    # Query invoices
    query = db.query(Invoice).filter(Invoice.firm_id == firm_id)
    
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    
    invoices = query.order_by(Invoice.invoice_date.desc()).limit(limit).all()
    
    # Convert to response models
    invoice_responses = [
        InvoiceResponse(
            id=inv.id,
            invoice_number=inv.invoice_number,
            amount=inv.amount,
            currency=inv.currency,
            invoice_date=inv.invoice_date.isoformat(),
            due_date=inv.due_date.isoformat(),
            status=inv.status.value,
            description=inv.description,
            paid_date=inv.paid_date.isoformat() if inv.paid_date else None
        )
        for inv in invoices
    ]
    
    # Calculate totals
    total_amount = sum(inv.amount for inv in invoices)
    pending_amount = sum(inv.amount for inv in invoices if inv.status == InvoiceStatus.PENDING)
    
    return InvoiceListResponse(
        firm_id=firm_id,
        firm_name=firm.name,
        invoices=invoice_responses,
        total_invoices=len(invoices),
        total_amount=total_amount,
        pending_amount=pending_amount
    )


@router.post("/invoice/generate")
async def generate_monthly_invoice(
    request: Request,
    month: int,
    year: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new monthly invoice for the firm.
    Only accessible by firm admins.
    
    Query Parameters:
    - month: Month (1-12)
    - year: Year (e.g., 2025)
    """
    # Only admins can generate invoices
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only firm administrators can generate invoices"
        )
    
    firm_id = get_current_firm_id(request)
    
    invoice = BillingService.generate_invoice(db, firm_id, month, year)
    
    return InvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        amount=invoice.amount,
        currency=invoice.currency,
        invoice_date=invoice.invoice_date.isoformat(),
        due_date=invoice.due_date.isoformat(),
        status=invoice.status.value,
        description=invoice.description,
        paid_date=None
    )


@router.get("/firm-stats")
async def get_firm_stats(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive firm statistics for dashboard.
    Includes usage metrics, subscription info, and ROI calculations.
    """
    from ..models import Document, Expediente
    from datetime import datetime
    
    firm_id = get_current_firm_id(request)
    
    # Get firm details
    firm = db.query(Firm).filter(Firm.id == firm_id).first()
    if not firm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Firm not found"
        )
    
    # Count resources (all filtered by firm_id)
    num_documents = db.query(Document).filter(Document.firm_id == firm_id).count()
    num_users = db.query(User).filter(User.firm_id == firm_id, User.is_active == True).count()
    num_expedientes = db.query(Expediente).filter(Expediente.firm_id == firm_id).count()
    
    # Calculate time & money saved
    # Assumption: Each document saves 30 minutes of manual work
    hours_saved = num_documents * 0.5
    # Average lawyer hourly rate in Morocco: 400 MAD/hour
    money_saved_mad = hours_saved * 400
    
    # Calculate subscription days remaining
    if firm.subscription_end:
        days_remaining = (firm.subscription_end - date.today()).days
    else:
        days_remaining = 0
    
    # Calculate storage usage (approximation: 2MB per document average)
    storage_used_gb = round((num_documents * 2) / 1024, 2) if num_documents > 0 else 0
    
    # Get next billing date from subscription
    subscription = db.query(Subscription).filter(Subscription.firm_id == firm_id).first()
    next_billing_date = subscription.next_billing_date if subscription else None
    
    return {
        "firm_name": firm.name,
        "subscription_status": firm.subscription_status.value,
        "subscription_tier": firm.subscription_tier.value,
        "subscription_end": firm.subscription_end.isoformat() if firm.subscription_end else None,
        "days_remaining": days_remaining,
        "is_active": firm.subscription_status == SubscriptionStatus.ACTIVE,
        
        # Usage statistics
        "documents_count": num_documents,
        "users_count": num_users,
        "expedientes_count": num_expedientes,
        
        # ROI calculations
        "time_saved_hours": round(hours_saved, 1),
        "money_saved_mad": round(money_saved_mad),
        
        # Storage
        "storage_used_gb": storage_used_gb,
        "max_storage_gb": firm.max_storage_gb,
        "storage_percentage": round((storage_used_gb / firm.max_storage_gb) * 100, 1) if firm.max_storage_gb > 0 else 0,
        
        # Billing
        "next_billing_date": next_billing_date.isoformat() if next_billing_date else None,
        "monthly_fee": subscription.monthly_cost if subscription else 0,
        
        # Limits
        "max_users": firm.max_users,
        "users_percentage": round((num_users / firm.max_users) * 100, 1) if firm.max_users > 0 else 0,
        "max_documents": firm.max_documents,
        "documents_percentage": round((num_documents / firm.max_documents) * 100, 1) if firm.max_documents > 0 else 0
    }
