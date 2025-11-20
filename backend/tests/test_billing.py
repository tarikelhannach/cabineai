import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.models import Firm, SubscriptionStatus

client = TestClient(app)

@patch("app.services.stripe_service.stripe")
def test_create_checkout_session(mock_stripe, db_session, test_user_token, test_firm):
    """Test creating a checkout session"""
    
    # Mock Stripe responses
    mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/test")
    
    # Call endpoint
    response = client.post(
        "/api/billing/create-checkout-session",
        json={"plan": "pro"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["url"] == "https://checkout.stripe.com/test"
    
    # Verify DB update (customer_id)
    db_session.refresh(test_firm)
    assert test_firm.stripe_customer_id == "cus_test123"
    
    # Verify line_items call to Stripe
    call_args = mock_stripe.checkout.Session.create.call_args
    assert call_args is not None
    line_items = call_args[1]['line_items']
    
    # Should have 2 items: Plan + Setup Fee (since firm is new)
    assert len(line_items) == 2
    assert line_items[1]['price'] == 'price_setup_fee_test'

def test_stripe_webhook(db_session, test_firm):
    """Test handling a successful payment webhook"""
    
    # Setup firm with customer_id
    test_firm.stripe_customer_id = "cus_test123"
    db_session.commit()
    
    # Mock webhook payload
    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_test123",
                "subscription": "sub_test456"
            }
        }
    }
    
    # Mock signature verification
    with patch("app.services.stripe_service.stripe.Webhook.construct_event") as mock_verify:
        mock_verify.return_value = payload
        
        response = client.post(
            "/api/billing/webhook",
            json=payload,
            headers={"stripe-signature": "test_sig"}
        )
        
        assert response.status_code == 200
        
        # Verify DB update (subscription status)
        db_session.refresh(test_firm)
        assert test_firm.stripe_subscription_id == "sub_test456"
        assert test_firm.subscription_status == SubscriptionStatus.ACTIVE
        assert test_firm.implementation_fee_paid is True
