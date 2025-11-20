import stripe
from fastapi import HTTPException
import os
from typing import Optional, Dict, Any

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

class StripeService:
    def __init__(self):
        if not stripe.api_key:
            print("WARNING: STRIPE_SECRET_KEY not set")

    def create_customer(self, email: str, name: str) -> str:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
            )
            return customer.id
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    def create_checkout_session(self, customer_id: str, price_id: Optional[str] = None, line_items: Optional[list] = None, success_url: str = "", cancel_url: str = "") -> str:
        """Create a checkout session for subscription"""
        try:
            if not line_items and price_id:
                line_items = [{
                    'price': price_id,
                    'quantity': 1,
                }]
            
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=line_items,
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create a customer portal session for managing subscriptions"""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    def construct_event(self, payload: bytes, sig_header: str) -> stripe.Event:
        """Verify and construct webhook event"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail="Invalid signature")
