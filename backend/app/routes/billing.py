from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Firm, SubscriptionStatus, SubscriptionTier
from app.auth.jwt import get_current_user
from app.services.stripe_service import StripeService
from pydantic import BaseModel
import os

router = APIRouter(prefix="/api/billing", tags=["billing"])
stripe_service = StripeService()

# Configuration
STRIPE_PRICE_ID_BASIC = os.getenv("STRIPE_PRICE_ID_BASIC", "price_basic_test")
STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO", "price_pro_test")
STRIPE_PRICE_ID_SETUP = os.getenv("STRIPE_PRICE_ID_SETUP", "price_setup_fee_test")

class CheckoutRequest(BaseModel):
    plan: str  # "basic" or "pro"

@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a Stripe Checkout session for subscription"""
    
    # 1. Get Firm
    firm = db.query(Firm).filter(Firm.id == current_user.firm_id).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")
    
    # 2. Create Stripe Customer if not exists
    if not firm.stripe_customer_id:
        customer_id = stripe_service.create_customer(firm.email, firm.name)
        firm.stripe_customer_id = customer_id
        db.commit()
    
    # 3. Select Price
    price_id = STRIPE_PRICE_ID_PRO if request.plan == "pro" else STRIPE_PRICE_ID_BASIC
    
    line_items = [{
        'price': price_id,
        'quantity': 1,
    }]
    
    # Add Setup Fee if not paid
    if not firm.implementation_fee_paid:
        line_items.append({
            'price': STRIPE_PRICE_ID_SETUP,
            'quantity': 1,
        })
    
    # 4. Create Session
    domain = os.getenv("FRONTEND_URL", "http://localhost:3000")
    session_url = stripe_service.create_checkout_session(
        customer_id=firm.stripe_customer_id,
        price_id=None, # We use line_items now
        line_items=line_items, # Pass line_items instead of single price
        success_url=f"{domain}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{domain}/billing/cancel"
    )
    
    return {"url": session_url}

@router.get("/portal")
async def customer_portal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Redirect to Stripe Customer Portal"""
    firm = db.query(Firm).filter(Firm.id == current_user.firm_id).first()
    if not firm or not firm.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No billing account found")
        
    domain = os.getenv("FRONTEND_URL", "http://localhost:3000")
    url = stripe_service.create_portal_session(firm.stripe_customer_id, f"{domain}/settings")
    return {"url": url}

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe Webhooks"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe_service.construct_event(payload, sig_header)
    except HTTPException as e:
        raise e
        
    # Handle events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_id = session['customer']
        subscription_id = session['subscription']
        
        # Update Firm
        firm = db.query(Firm).filter(Firm.stripe_customer_id == customer_id).first()
        if firm:
            firm.stripe_subscription_id = subscription_id
            firm.subscription_status = SubscriptionStatus.ACTIVE
            # If successful, we assume setup fee is paid (if it was in the cart)
            # In a real scenario, we might check line_items of the session
            firm.implementation_fee_paid = True 
            db.commit()
            
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription['customer']
        
        firm = db.query(Firm).filter(Firm.stripe_customer_id == customer_id).first()
        if firm:
            firm.subscription_status = SubscriptionStatus.EXPIRED
            db.commit()
            
    return {"status": "success"}
