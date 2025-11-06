"""
Billing Service for Subscription Management and Invoice Generation
Handles all subscription validation, fee calculation, and billing operations
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

from ..models import (
    Firm, Subscription, Invoice, User, UserRole,
    SubscriptionStatus, SubscriptionTier, InvoiceStatus
)


class BillingService:
    """Service for managing firm subscriptions and billing"""
    
    # Pricing constants (in MAD - Moroccan Dirham)
    MONTHLY_FEE_PER_LAWYER = 270
    IMPLEMENTATION_FEE_BASIC = 20600
    IMPLEMENTATION_FEE_COMPLETE = 30600
    
    @staticmethod
    def calculate_monthly_fee(db: Session, firm_id: int) -> float:
        """
        Calculate the monthly subscription fee for a firm.
        Fee = num_lawyers × 270 MAD
        
        Args:
            db: Database session
            firm_id: ID of the firm
            
        Returns:
            Monthly fee amount in MAD
        """
        # Count active lawyers in the firm
        num_lawyers = db.query(func.count(User.id)).filter(
            User.firm_id == firm_id,
            User.role == UserRole.LAWYER,
            User.is_active == True
        ).scalar()
        
        # Get firm to check monthly fee (in case of custom pricing)
        firm = db.query(Firm).filter(Firm.id == firm_id).first()
        if not firm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Firm {firm_id} not found"
            )
        
        # Use firm's monthly fee per lawyer (allows for custom pricing)
        fee_per_lawyer = firm.monthly_fee_per_lawyer or BillingService.MONTHLY_FEE_PER_LAWYER
        
        return num_lawyers * fee_per_lawyer
    
    @staticmethod
    def check_subscription_status(db: Session, firm_id: int) -> Dict[str, Any]:
        """
        Check the subscription status of a firm.
        
        Args:
            db: Database session
            firm_id: ID of the firm
            
        Returns:
            Dictionary with subscription status details
        """
        firm = db.query(Firm).filter(Firm.id == firm_id).first()
        if not firm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Firm {firm_id} not found"
            )
        
        subscription = db.query(Subscription).filter(
            Subscription.firm_id == firm_id
        ).first()
        
        if not subscription:
            return {
                "firm_id": firm_id,
                "firm_name": firm.name,
                "status": "no_subscription",
                "is_active": False,
                "message": "No subscription found for this firm"
            }
        
        # Check if subscription has expired
        is_active = subscription.status == SubscriptionStatus.ACTIVE
        
        if subscription.end_date and subscription.end_date < date.today():
            is_active = False
            # Update subscription status if expired
            subscription.status = SubscriptionStatus.EXPIRED
            firm.subscription_status = SubscriptionStatus.EXPIRED
            db.commit()
        
        return {
            "firm_id": firm_id,
            "firm_name": firm.name,
            "status": subscription.status.value,
            "is_active": is_active,
            "tier": subscription.plan_tier.value,
            "start_date": subscription.start_date.isoformat() if subscription.start_date else None,
            "end_date": subscription.end_date.isoformat() if subscription.end_date else None,
            "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
            "monthly_cost": subscription.monthly_cost
        }
    
    @staticmethod
    def validate_active_subscription(db: Session, firm_id: int) -> bool:
        """
        Validate that a firm has an active subscription.
        Raises HTTPException if subscription is not active.
        
        Args:
            db: Database session
            firm_id: ID of the firm
            
        Returns:
            True if subscription is active
            
        Raises:
            HTTPException: If subscription is not active
        """
        status_info = BillingService.check_subscription_status(db, firm_id)
        
        if not status_info["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "subscription_inactive",
                    "message": "Your subscription is not active. Please renew to continue using the service.",
                    "status": status_info["status"],
                    "firm_id": firm_id
                }
            )
        
        return True
    
    @staticmethod
    def generate_invoice(
        db: Session,
        firm_id: int,
        month: int,
        year: int,
        description: Optional[str] = None
    ) -> Invoice:
        """
        Generate a monthly invoice for a firm.
        
        Args:
            db: Database session
            firm_id: ID of the firm
            month: Month for the invoice (1-12)
            year: Year for the invoice
            description: Optional invoice description
            
        Returns:
            Created Invoice object
        """
        # Validate month and year
        if not (1 <= month <= 12):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month. Must be between 1 and 12."
            )
        
        # Check if invoice already exists for this period
        invoice_number = f"INV-{firm_id}-{year}{month:02d}"
        existing_invoice = db.query(Invoice).filter(
            Invoice.invoice_number == invoice_number
        ).first()
        
        if existing_invoice:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invoice for {year}-{month:02d} already exists"
            )
        
        # Calculate monthly fee
        monthly_fee = BillingService.calculate_monthly_fee(db, firm_id)
        
        # Create invoice
        invoice_date = date(year, month, 1)
        due_date = invoice_date + timedelta(days=30)  # 30 days payment term
        
        if not description:
            description = f"Monthly subscription fee for {year}-{month:02d}"
        
        invoice = Invoice(
            firm_id=firm_id,
            invoice_number=invoice_number,
            amount=monthly_fee,
            currency="MAD",
            invoice_date=invoice_date,
            due_date=due_date,
            status=InvoiceStatus.PENDING,
            description=description
        )
        
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        return invoice
    
    @staticmethod
    def initialize_firm_subscription(
        db: Session,
        firm_id: int,
        tier: SubscriptionTier,
        duration_months: int = 36
    ) -> Subscription:
        """
        Initialize a new subscription for a firm.
        Used during firm onboarding.
        
        Args:
            db: Database session
            firm_id: ID of the firm
            tier: Subscription tier (BASIC or COMPLETE)
            duration_months: Subscription duration in months (default 36 for GPU coverage)
            
        Returns:
            Created Subscription object
        """
        firm = db.query(Firm).filter(Firm.id == firm_id).first()
        if not firm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Firm {firm_id} not found"
            )
        
        # Check if subscription already exists
        existing_subscription = db.query(Subscription).filter(
            Subscription.firm_id == firm_id
        ).first()
        
        if existing_subscription:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Firm already has a subscription"
            )
        
        # Calculate initial monthly cost
        monthly_cost = BillingService.calculate_monthly_fee(db, firm_id)
        
        # Set subscription dates
        start_date = date.today()
        end_date = start_date + timedelta(days=duration_months * 30)
        next_billing = start_date + timedelta(days=30)
        
        # Create subscription
        subscription = Subscription(
            firm_id=firm_id,
            status=SubscriptionStatus.ACTIVE,
            start_date=start_date,
            end_date=end_date,
            plan_tier=tier,
            monthly_cost=monthly_cost,
            next_billing_date=next_billing,
            auto_renew=True
        )
        
        # Update firm status
        firm.subscription_tier = tier
        firm.subscription_status = SubscriptionStatus.ACTIVE
        firm.subscription_start = start_date
        firm.subscription_end = end_date
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        # Generate first invoice including implementation fee
        current_month = start_date.month
        current_year = start_date.year
        
        # Create implementation fee invoice
        implementation_fee = (
            BillingService.IMPLEMENTATION_FEE_COMPLETE 
            if tier == SubscriptionTier.COMPLETE 
            else BillingService.IMPLEMENTATION_FEE_BASIC
        )
        
        implementation_invoice = Invoice(
            firm_id=firm_id,
            invoice_number=f"INV-{firm_id}-IMPL-{current_year}{current_month:02d}",
            amount=implementation_fee,
            currency="MAD",
            invoice_date=start_date,
            due_date=start_date + timedelta(days=7),  # 7 days for implementation fee
            status=InvoiceStatus.PENDING,
            description=f"Implementation fee - {tier.value.title()} Plan (includes GPU, training, {'digitization' if tier == SubscriptionTier.COMPLETE else 'setup'})"
        )
        db.add(implementation_invoice)
        
        # Only generate first monthly invoice if there are active lawyers
        if monthly_cost > 0:
            monthly_invoice = BillingService.generate_invoice(
                db, firm_id, current_month, current_year,
                description=f"Monthly subscription - {tier.value.title()} Plan"
            )
        
        db.commit()
        
        return subscription
