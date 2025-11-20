import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import Firm, User, Case, Document, UserRole, SubscriptionStatus, SubscriptionTier, CaseStatus
from app.auth.auth import get_password_hash, create_access_token

# -----------------------------------------------------------------------------
# FIXTURES LOCALES PARA AISLAMIENTO
# -----------------------------------------------------------------------------

@pytest.fixture(scope="function")
def firm_a(db_session: Session) -> Firm:
    firm = Firm(
        name="Firm A - Legal Corp",
        email="contact@firma.ma",
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_tier=SubscriptionTier.COMPLETE
    )
    db_session.add(firm)
    db_session.commit()
    db_session.refresh(firm)
    return firm

@pytest.fixture(scope="function")
def firm_b(db_session: Session) -> Firm:
    firm = Firm(
        name="Firm B - Another Corp",
        email="contact@firmb.ma",
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_tier=SubscriptionTier.BASIC
    )
    db_session.add(firm)
    db_session.commit()
    db_session.refresh(firm)
    return firm

@pytest.fixture(scope="function")
def user_a(db_session: Session, firm_a: Firm) -> User:
    user = User(
        email="admin@firma.ma",
        name="Admin Firm A",
        hashed_password=get_password_hash("password123"),
        role=UserRole.ADMIN,
        firm_id=firm_a.id,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def user_b(db_session: Session, firm_b: Firm) -> User:
    user = User(
        email="admin@firmb.ma",
        name="Admin Firm B",
        hashed_password=get_password_hash("password123"),
        role=UserRole.ADMIN,
        firm_id=firm_b.id,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def token_a(user_a: User) -> str:
    return create_access_token({"sub": user_a.email, "user_id": user_a.id})

@pytest.fixture(scope="function")
def token_b(user_b: User) -> str:
    return create_access_token({"sub": user_b.email, "user_id": user_b.id})

@pytest.fixture(scope="function")
def case_a(db_session: Session, firm_a: Firm, user_a: User) -> Case:
    case = Case(
        expediente_number="CASE-A-001",
        client_name="Client A",
        description="Confidential Firm A",
        status=CaseStatus.PENDING,
        firm_id=firm_a.id,
        owner_id=user_a.id
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case

# -----------------------------------------------------------------------------
# TESTS DE AISLAMIENTO
# -----------------------------------------------------------------------------

def test_case_isolation(client: TestClient, token_a: str, token_b: str, case_a: Case):
    """Verify User B cannot see Case A"""
    
    # 1. User A should see the case
    response = client.get(
        f"/api/cases/{case_a.id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert response.status_code == 200
    assert response.json()["expediente_number"] == "CASE-A-001"

    # 2. User B should NOT see the case (404 Not Found is preferred over 403 to avoid leaking existence)
    response = client.get(
        f"/api/cases/{case_a.id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Caso no encontrado"

def test_user_list_isolation(client: TestClient, token_a: str, token_b: str, user_a: User, user_b: User):
    """Verify User A only sees users from Firm A"""
    
    # User A requests user list
    response = client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert response.status_code == 200
    users = response.json()
    
    # Should contain User A
    user_ids = [u["id"] for u in users]
    assert user_a.id in user_ids
    
    # Should NOT contain User B
    assert user_b.id not in user_ids

def test_create_user_isolation(client: TestClient, token_a: str, db_session: Session, firm_a: Firm):
    """Verify created user is assigned to creator's firm"""
    
    new_user_data = {
        "name": "New Employee",
        "email": "new@firma.ma",
        "password": "password123",
        "role": "lawyer"
    }
    
    response = client.post(
        "/api/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert response.status_code == 201
    created_id = response.json()["id"]
    
    # Verify in DB
    created_user = db_session.query(User).filter(User.id == created_id).first()
    assert created_user.firm_id == firm_a.id

def test_cross_tenant_update_prevention(client: TestClient, token_b: str, user_a: User):
    """Verify User B cannot update User A"""
    
    update_data = {"name": "Hacked Name"}
    
    response = client.put(
        f"/api/users/{user_a.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token_b}"}
    )
    
    # Should return 404 (User not found in Firm B)
    assert response.status_code == 404
