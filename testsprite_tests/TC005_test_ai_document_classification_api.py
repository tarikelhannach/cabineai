import requests
import io

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

# Assuming authentication is required, define login credentials here
AUTH_EMAIL = "admin@example.com"
AUTH_PASSWORD = "StrongPassword123!"


def get_auth_token():
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AUTH_EMAIL, "password": AUTH_PASSWORD},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        raise RuntimeError(f"Authentication failed: {e}")


def upload_sample_document(auth_token):
    try:
        # Create an in-memory dummy pdf file
        file_content = b"%PDF-1.4\n%Dummy PDF file for testing\n"
        dummy_file = io.BytesIO(file_content)
        dummy_file.name = "sample_document.pdf"  # Some servers may require filename

        headers = {"Authorization": f"Bearer {auth_token}"}
        files = {"file": (dummy_file.name, dummy_file, "application/pdf")}
        payload = {"case_id": "1"}  # case_id sent as string form field
        response = requests.post(
            f"{BASE_URL}/api/documents/upload",
            headers=headers,
            files=files,
            data=payload,
            timeout=TIMEOUT,
        )
        dummy_file.close()
        response.raise_for_status()
        json_data = response.json()
        document_id = json_data.get("document_id")
        assert document_id is not None, "Upload response missing 'document_id'"
        return document_id
    except Exception as e:
        raise RuntimeError(f"Document upload failed: {e}")


def delete_document(auth_token, document_id):
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.delete(
            f"{BASE_URL}/api/documents/{document_id}", headers=headers, timeout=TIMEOUT
        )
        response.raise_for_status()
    except Exception as e:
        # Log error but do not re-raise to ensure test teardown completes
        print(f"Warning: Failed to delete document {document_id}: {e}")


def test_ai_document_classification_api():
    auth_token = get_auth_token()
    assert auth_token is not None, "Failed to obtain auth token"

    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

    document_id = None
    try:
        # Upload a sample document to classify
        document_id = upload_sample_document(auth_token)
        assert document_id is not None, "Uploaded document_id is None"

        # Trigger AI classification
        response = requests.post(
            f"{BASE_URL}/api/documents/{document_id}/classify",
            headers=headers,
            timeout=TIMEOUT,
        )

        # Validate response status code
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

        classification_result = response.json()
        # Validate that classification result contains expected keys
        assert isinstance(classification_result, dict), "Classification result is not a dict"
        assert len(classification_result) > 0, (
            "Classification result missing expected classification data"
        )

    finally:
        if document_id:
            delete_document(auth_token, document_id)


test_ai_document_classification_api()