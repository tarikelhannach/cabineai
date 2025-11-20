import requests

BASE_URL = "http://localhost:8000"


def test_user_login_api():
    url = f"{BASE_URL}/api/auth/login"
    headers = {
        "Content-Type": "application/json"
    }
    # Use valid credentials for testing
    payload = {
        "email": "testuser@example.com",
        "password": "TestPassword123!"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    json_response = response.json()
    assert "access_token" in json_response, "access_token is missing in response"
    assert isinstance(json_response["access_token"], str) and len(json_response["access_token"]) > 0, "Invalid access_token"
    assert "token_type" in json_response, "token_type is missing in response"
    assert json_response["token_type"].lower() == "bearer", "token_type should be 'bearer'"
    assert "user" in json_response, "user details missing in response"
    assert isinstance(json_response["user"], dict), "user should be an object"

    # Optionally check expected fields inside user object
    user = json_response["user"]
    assert "email" in user, "user object missing 'email'"
    assert user["email"].lower() == payload["email"].lower(), "Returned user email does not match login email"


test_user_login_api()