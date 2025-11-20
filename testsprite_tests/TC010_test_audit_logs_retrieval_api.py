import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_audit_logs_retrieval_api():
    url = f"{BASE_URL}/api/audit/logs"
    headers = {
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to /api/audit/logs failed with exception: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    # Basic validation of audit logs structure: expect a list or dict with audit logs
    assert isinstance(data, (list, dict)), "Response JSON should be a list or dict"

    # If list, check elements have expected keys for audit logs
    if isinstance(data, list) and len(data) > 0:
        first_log = data[0]
        assert isinstance(first_log, dict), "Each audit log entry should be a dict"
        # Check presence of typical audit log fields
        expected_keys = {"timestamp", "user_id", "action", "resource", "details"}
        missing_keys = expected_keys - first_log.keys()
        assert not missing_keys, f"Audit log entry missing keys: {missing_keys}"
    elif isinstance(data, dict):
        # If dict, check it contains keys for audit log data
        # This is generic since the schema is not specified
        assert len(data) > 0, "Audit logs dict response should not be empty"

test_audit_logs_retrieval_api()