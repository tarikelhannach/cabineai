import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Document, User, Firm
from app.database import get_db

client = TestClient(app)

def test_update_ocr_verification(db_session, test_user_token, test_document):
    """Test the OCR verification endpoint"""
    
    # 1. Verify initial state
    assert test_document.is_verified is False
    assert test_document.verified_at is None
    
    # 2. Call the endpoint
    new_text = "This is the verified text."
    response = client.put(
        f"/api/documents/{test_document.id}/ocr",
        json={"ocr_text": new_text},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    # 3. Check response
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "OCR updated and verified successfully"
    assert data["is_verified"] is True
    
    # 4. Verify database update
    db_session.refresh(test_document)
    assert test_document.ocr_text == new_text
    assert test_document.is_verified is True
    assert test_document.verified_at is not None
