import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_case_creation_api():
    url = f"{BASE_URL}/api/cases/"
    headers = {
        "Content-Type": "application/json"
    }
    # Minimal valid payload for case creation
    payload = {
        "title": "New Legal Case Example"
    }

    response = None
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 201, f"Expected status code 201, got {response.status_code}"
        json_resp = response.json()
        # Validate response contains expected fields and matches input data
        assert "id" in json_resp, "Response missing 'id' field"
        assert json_resp.get("title") == payload["title"], "Title mismatch"
    finally:
        if response is not None and response.status_code == 201:
            created_case_id = response.json().get("id")
            if created_case_id:
                del_url = f"{BASE_URL}/api/cases/{created_case_id}"
                try:
                    del_response = requests.delete(del_url, timeout=TIMEOUT)
                    assert del_response.status_code == 204, f"Failed to delete created case with id {created_case_id}"
                except Exception as e:
                    # Just raise if deletion fails, so cleanup issues are visible
                    raise e

test_case_creation_api()
