import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_billing_create_checkout_session_api():
    url = f"{BASE_URL}/api/billing/create-checkout-session"
    headers = {
        "Content-Type": "application/json",
    }
    # Example payload for creating a checkout session, adjust as necessary
    payload = {
        "mode": "subscription",
        "line_items": [
            {
                "price": "price_12345",  # Replace with valid Stripe price ID for subscription
                "quantity": 1
            }
        ],
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to create checkout session failed: {e}"

    content_type = response.headers.get("Content-Type", "")
    assert "application/json" in content_type, \
        f"Response content-type is not application/json, got: {content_type}"

    data = response.json()
    assert isinstance(data, dict), f"Response JSON is not an object: {data}"

    assert "id" in data, f"Response missing 'id' field: {data}"
    assert isinstance(data["id"], str), f"Response 'id' is not a string: {data['id']}"
    assert data["id"].startswith("cs_"), f"Response 'id' does not start with 'cs_': {data['id']}"

    assert "url" in data, f"Response missing 'url' field: {data}"
    assert isinstance(data["url"], str), f"Response 'url' is not a string: {data['url']}"
    assert data["url"].startswith("http"), f"Response 'url' does not start with 'http': {data['url']}"

    if "mode" in data:
        assert data["mode"] == "subscription", f"Checkout session mode is not 'subscription', got: {data['mode']}"
    if "payment_status" in data:
        assert data["payment_status"] in {"unpaid", "paid"}, f"Invalid payment status in checkout session response: {data['payment_status']}"

test_billing_create_checkout_session_api()
