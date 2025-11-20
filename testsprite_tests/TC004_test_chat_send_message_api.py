import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_chat_send_message_api():
    url = f"{BASE_URL}/api/chat/messages"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "message": "Hello, can you help me understand the process for filing a legal claim in Morocco?"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to {url} failed: {e}"

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"

    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    # Validate AI-generated response presence and type
    assert "response" in data, "Response does not contain AI-generated response"
    ai_response = data.get("response")
    assert isinstance(ai_response, str), "AI-generated response is not a string"
    assert len(ai_response) > 0, "AI-generated response is empty"

test_chat_send_message_api()
