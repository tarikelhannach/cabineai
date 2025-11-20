"""
Multi-Tenant Database Initialization Script
Creates tables and sets up example firm for JusticeAI Commercial
"""

import sys
import os
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.models import (
    Base, Firm, User, Expediente, Document, AuditLog,
    Subscription, Invoice,
    SubscriptionTier, SubscriptionStatus, UserRole,
    LanguagePreference, CaseStatus, CaseType, Priority, InvoiceStatus
)
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_database():
    """Initialize database schema"""
    print("🔧 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def create_example_firm():
    """Create an example law firm with users for testing"""
    db = SessionLocal()
    
    try:
        # Check if example firm already exists
        existing_firm = db.query(Firm).filter(Firm.email == "contact@cabinet-demo.ma").first()
        if existing_firm:
            print("⚠️  Example firm already exists, skipping creation")
            return
        
        print("\n📝 Creating example law firm...")
        
        # Create firm
        firm = Firm(
            name="Cabinet d'Avocats Demo",
            email="contact@cabinet-demo.ma",
            phone="+212 5 22 XX XX XX",
            address="123 Avenue Mohammed V, Casablanca, Maroc",
            subscription_tier=SubscriptionTier.COMPLETE,
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_start=date.today(),
            subscription_end=date.today() + timedelta(days=1095),  # 3 years
            implementation_fee_paid=True,
            monthly_fee_per_lawyer=270,
            language_preference=LanguagePreference.FRENCH,
            max_users=50,
            max_documents=100000,
            max_storage_gb=500
        )
        
        db.add(firm)
        db.flush()
        
        print(f"✅ Firm created: {firm.name} (ID: {firm.id})")
        
        # Create subscription
        subscription = Subscription(
            firm_id=firm.id,
            status=SubscriptionStatus.ACTIVE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1095),
            plan_tier=SubscriptionTier.COMPLETE,
            monthly_cost=1620.0,  # 6 lawyers × 270 MAD
            next_billing_date=date.today() + timedelta(days=30),
            auto_renew=True
        )
        
        db.add(subscription)
        print(f"✅ Subscription created for firm {firm.id}")
        
        # Create users
        users_data = [
            {
                "name": "Fatima El Mansouri",
                "email": "fatima@cabinet-demo.ma",
                "role": UserRole.ADMIN,
                "language": LanguagePreference.FRENCH
            },
            {
                "name": "Ahmed Benjelloun",
                "email": "ahmed@cabinet-demo.ma",
                "role": UserRole.LAWYER,
                "language": LanguagePreference.FRENCH
            },
            {
                "name": "Sara Alami",
                "email": "sara@cabinet-demo.ma",
                "role": UserRole.LAWYER,
                "language": LanguagePreference.FRENCH
            },
            {
                "name": "Omar Tazi",
                "email": "omar@cabinet-demo.ma",
                "role": UserRole.LAWYER,
                "language": LanguagePreference.ARABIC
            },
            {
                "name": "Leila Fassi",
                "email": "leila@cabinet-demo.ma",
                "role": UserRole.LAWYER,
                "language": LanguagePreference.FRENCH
            },
            {
                "name": "Hassan Chraibi",
                "email": "hassan@cabinet-demo.ma",
                "role": UserRole.LAWYER,
                "language": LanguagePreference.ARABIC
            },
            {
                "name": "Nadia Berrada",
                "email": "nadia@cabinet-demo.ma",
                "role": UserRole.ASSISTANT,
                "language": LanguagePreference.FRENCH
            }
        ]
        
        # Default password for all demo users: "Demo2025!"
        default_password = pwd_context.hash("Demo2025!")
        
        created_users = []
        for user_data in users_data:
            user = User(
                firm_id=firm.id,
                email=user_data["email"],
                name=user_data["name"],
                hashed_password=default_password,
                role=user_data["role"],
                language=user_data["language"],
                is_active=True,
                is_verified=True
            )
            db.add(user)
            created_users.append(user)
        
        db.flush()
        
        print(f"✅ Created {len(created_users)} users")
        for user in created_users:
            print(f"   - {user.name} ({user.role.value}) - {user.email}")
        
        # Create implementation fee invoice
        impl_invoice = Invoice(
            firm_id=firm.id,
            invoice_number=f"INV-{firm.id}-IMPL-202501",
            amount=30600.0,  # Complete tier implementation fee
            currency="MAD",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            status=InvoiceStatus.PAID,
            description="Implementation fee - Complete Plan (includes GPU, training, digitization of 50K pages)",
            paid_date=date.today()
        )
        db.add(impl_invoice)
        
        # Create first monthly invoice
        monthly_invoice = Invoice(
            firm_id=firm.id,
            invoice_number=f"INV-{firm.id}-202501",
            amount=1620.0,  # 6 lawyers × 270 MAD
            currency="MAD",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=InvoiceStatus.PENDING,
            description="Monthly subscription - January 2025 (6 lawyers)"
        )
        db.add(monthly_invoice)
        
        print(f"✅ Created 2 invoices (implementation + monthly)")
        
        # Create example expediente
        admin_user = next(u for u in created_users if u.role == UserRole.ADMIN)
        lawyer_user = next(u for u in created_users if u.role == UserRole.LAWYER)
        
        expediente = Expediente(
            firm_id=firm.id,
            expediente_number="EXP-2025-001",
            client_name="Société ABC SARL",
            matter_type=CaseType.COMMERCIAL,
            description="Litige commercial concernant un contrat de distribution",
            status=CaseStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            owner_id=admin_user.id,
            assigned_lawyer_id=lawyer_user.id
        )
        db.add(expediente)
        
        print(f"✅ Created example expediente: {expediente.expediente_number}")
        
        db.commit()
        
        print("\n" + "="*60)
        print("✨ EXAMPLE FIRM SETUP COMPLETE ✨")
        print("="*60)
        print(f"\nFirm Details:")
        print(f"  Name: {firm.name}")
        print(f"  Email: {firm.email}")
        print(f"  Subscription: {subscription.plan_tier.value.title()} (Active)")
        print(f"  Users: {len(created_users)}")
        print(f"\nLogin Credentials (all users):")
        print(f"  Password: Demo2025!")
        print(f"\nExample Users:")
        print(f"  Admin: fatima@cabinet-demo.ma")
        print(f"  Lawyer: ahmed@cabinet-demo.ma")
        print(f"  Assistant: nadia@cabinet-demo.ma")
        print("\n" + "="*60)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating example firm: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("🚀 JusticeAI Commercial - Multi-Tenant Database Setup")
    print("="*60)
    
    try:
        # Initialize database
        init_database()
        
        # Create example firm
        create_example_firm()
        
        print("\n✅ Database initialization complete!")
        print("\n📚 Next steps:")
        print("  1. Start the backend server: uvicorn app.main:app --reload")
        print("  2. Access API docs: http://localhost:8000/docs")
        print("  3. Test billing endpoint: POST /api/billing/status")
        print("  4. Login with: fatima@cabinet-demo.ma / Demo2025!")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
