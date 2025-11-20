import requests

BASE_URL = "http://localhost:8000"
USERS_ENDPOINT = f"{BASE_URL}/api/users/"
TIMEOUT = 30

def test_user_creation_api():
    headers = {
        "Content-Type": "application/json"
    }
    # Example valid user data with roles and permissions
    user_data = {
        "email": "testuser@example.com",
        "password": "StrongPassword!123",
        "first_name": "Test",
        "last_name": "User",
        "roles": ["lawyer", "editor"],
        "permissions": ["read_documents", "edit_documents", "upload_documents"]
    }

    created_user_id = None

    try:
        # Create user
        response = requests.post(
            USERS_ENDPOINT,
            json=user_data,
            headers=headers,
            timeout=TIMEOUT
        )
        assert response.status_code in (200, 201), f"Expected status 200 or 201, got {response.status_code}"
        resp_json = response.json()

        # If the user info is nested under 'user' key, adjust accordingly
        user_info = resp_json.get("user", resp_json)

        # Validate keys existence
        assert "id" in user_info, "Response missing user id"
        assert user_info.get("email") == user_data["email"], "Email mismatch in response"
        assert "roles" in user_info, "Roles missing in response"
        assert "permissions" in user_info, "Permissions missing in response"
        # Validate roles and permissions contain the assigned ones
        for role in user_data["roles"]:
            assert role in user_info["roles"], f"Role {role} missing in response"
        for perm in user_data["permissions"]:
            assert perm in user_info["permissions"], f"Permission {perm} missing in response"

        created_user_id = user_info["id"]

    finally:
        # Cleanup - delete the created user if created
        if created_user_id is not None:
            delete_url = f"{USERS_ENDPOINT}{created_user_id}"
            try:
                del_resp = requests.delete(delete_url, headers=headers, timeout=TIMEOUT)
                # Accept 200 or 204 as success in deletion
                assert del_resp.status_code in (200, 204), f"Failed to delete user, status {del_resp.status_code}"
            except Exception:
                pass

test_user_creation_api()
