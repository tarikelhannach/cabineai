import requests
import io

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_document_upload_api():
    # First, create a new case to associate the document with
    case_data = {
        "title": "Test Case for Document Upload",
        "description": "Case created for testing document upload"
    }
    headers = {"Accept": "application/json"}

    case_id = None
    document_id = None

    try:
        # Create case
        response_case = requests.post(f"{BASE_URL}/api/cases/", json=case_data, headers=headers, timeout=TIMEOUT)
        assert response_case.status_code in (200, 201), f"Failed to create case: {response_case.text}"
        case_resp_json = response_case.json()
        assert "id" in case_resp_json, f"Case creation response missing 'id': {case_resp_json}"
        case_id = case_resp_json["id"]

        # Prepare a dummy file-like object to upload
        dummy_content = b"Sample text content for test document upload."
        file_tuple = ('test_document.txt', io.BytesIO(dummy_content), 'text/plain')

        # Upload document with the created case_id
        files = {
            "file": file_tuple,
        }
        data = {
            "case_id": case_id,  # Pass as integer as per PRD
        }

        response_upload = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT
        )

        # Validate upload response
        assert response_upload.status_code in (200, 201), (
            f"Unexpected status code when uploading document: {response_upload.status_code}, response: {response_upload.text}"
        )
        resp_json = response_upload.json()
        # Check for indicators of success: presence of document ID or success flag
        assert resp_json is not None, "Empty response from document upload"
        if "id" in resp_json:
            document_id = resp_json["id"]
        elif "document_id" in resp_json:
            document_id = resp_json["document_id"]
        elif "success" in resp_json:
            assert resp_json["success"] is True, "Document upload did not return success True"
        else:
            assert len(resp_json) > 0, "No useful data in upload response"

    finally:
        # Clean up: Delete uploaded document (if any) and the case
        if document_id:
            try:
                del_resp = requests.delete(f"{BASE_URL}/api/documents/{document_id}", headers=headers, timeout=TIMEOUT)
                assert del_resp.status_code in (200, 204), f"Failed to delete document {document_id}"
            except Exception:
                pass
        if case_id:
            try:
                del_case_resp = requests.delete(f"{BASE_URL}/api/cases/{case_id}", headers=headers, timeout=TIMEOUT)
                assert del_case_resp.status_code in (200, 204), f"Failed to delete case {case_id}"
            except Exception:
                pass

test_document_upload_api()
