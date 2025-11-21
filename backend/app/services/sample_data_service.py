import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import (
    Expediente, Document, AuditLog, 
    CaseStatus, CaseType, Priority, 
    DocumentType, User
)

class SampleDataService:
    @staticmethod
    def generate_sample_data(db: Session, firm_id: int, user_id: int):
        """
        Generates sample data for a new firm to populate the dashboard.
        Creates:
        - 5 Cases (Expedientes) with mixed statuses
        - 8 Documents associated with these cases
        - 10 Audit Logs for recent activity
        """
        
        # 1. Create Sample Cases
        cases_data = [
            {
                "number": f"EXP-{datetime.now().year}-001",
                "client": "Société Immobilière Atlas",
                "type": CaseType.COMMERCIAL,
                "status": CaseStatus.IN_PROGRESS,
                "desc": "Litige commercial concernant le projet résidentiel Al-Andalus.",
                "priority": Priority.HIGH
            },
            {
                "number": f"EXP-{datetime.now().year}-002",
                "client": "Karim Benjelloun",
                "type": CaseType.CIVIL,
                "status": CaseStatus.PENDING,
                "desc": "Affaire de succession familiale et partage de biens.",
                "priority": Priority.MEDIUM
            },
            {
                "number": f"EXP-{datetime.now().year}-003",
                "client": "TechMaroc Solutions SARL",
                "type": CaseType.ADMINISTRATIVE,
                "status": CaseStatus.RESOLVED,
                "desc": "Recours administratif contre une décision fiscale.",
                "priority": Priority.HIGH
            },
            {
                "number": f"EXP-{datetime.now().year}-004",
                "client": "Fatima Zahra El Amrani",
                "type": CaseType.FAMILY,
                "status": CaseStatus.IN_PROGRESS,
                "desc": "Procédure de divorce et garde des enfants.",
                "priority": Priority.URGENT
            },
            {
                "number": f"EXP-{datetime.now().year}-005",
                "client": "Banque Populaire",
                "type": CaseType.COMMERCIAL,
                "status": CaseStatus.CLOSED,
                "desc": "Recouvrement de créances impayées.",
                "priority": Priority.LOW
            }
        ]

        created_cases = []
        for data in cases_data:
            case = Expediente(
                firm_id=firm_id,
                expediente_number=data["number"],
                client_name=data["client"],
                matter_type=data["type"],
                description=data["desc"],
                status=data["status"],
                priority=data["priority"],
                owner_id=user_id,
                assigned_lawyer_id=user_id,
                created_at=datetime.now() - timedelta(days=random.randint(1, 30))
            )
            db.add(case)
            created_cases.append(case)
        
        db.flush() # Get IDs

        # 2. Create Sample Documents (Mock)
        doc_types = ["Contrat.pdf", "Jugement.pdf", "Facture.pdf", "Preuve.jpg", "Rapport.docx"]
        
        for case in created_cases:
            # Add 1-3 documents per case
            for _ in range(random.randint(1, 3)):
                filename = random.choice(doc_types)
                doc = Document(
                    firm_id=firm_id,
                    filename=f"{case.expediente_number}_{filename}",
                    file_path=f"uploads/{firm_id}/{case.id}/{filename}", # Mock path
                    file_size=random.randint(1024, 5000000),
                    mime_type="application/pdf",
                    expediente_id=case.id,
                    uploaded_by=user_id,
                    created_at=case.created_at + timedelta(days=random.randint(0, 5)),
                    is_verified=random.choice([True, False])
                )
                db.add(doc)

        # 3. Create Audit Logs (Recent Activity)
        actions = [
            ("login", "Connexion au système"),
            ("create_case", "Création d'un nouveau dossier"),
            ("upload_document", "Téléchargement de document"),
            ("view_case", "Consultation de dossier"),
            ("update_status", "Mise à jour du statut")
        ]

        for i in range(10):
            action, details = random.choice(actions)
            log = AuditLog(
                firm_id=firm_id,
                user_id=user_id,
                action=action,
                details=details,
                ip_address="192.168.1.1",
                created_at=datetime.now() - timedelta(hours=random.randint(0, 48))
            )
            db.add(log)

        db.commit()
        return True
