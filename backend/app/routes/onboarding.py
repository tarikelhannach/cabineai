from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models import User, Firm, UserRole, LanguagePreference
from ..services.sample_data_service import SampleDataService
from .auth import get_current_active_user

router = APIRouter(
    prefix="/onboarding",
    tags=["onboarding"]
)

class OnboardingRequest(BaseModel):
    firm_name: str
    firm_address: Optional[str] = None
    language: str = "fr"
    generate_sample_data: bool = False

@router.post("/complete")
async def complete_onboarding(
    request: OnboardingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete the onboarding process for a new firm.
    Updates firm details and optionally generates sample data.
    """
    
    # 1. Update Firm Details
    firm = db.query(Firm).filter(Firm.id == current_user.firm_id).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")
    
    firm.name = request.firm_name
    if request.firm_address:
        firm.address = request.firm_address
    
    # Map language string to Enum
    try:
        lang_enum = LanguagePreference(request.language)
        firm.language_preference = lang_enum
        current_user.language = lang_enum
    except ValueError:
        pass # Keep default if invalid

    # 2. Generate Sample Data if requested
    if request.generate_sample_data:
        # Check if data already exists to prevent duplicates
        # For now, we rely on the user's choice. 
        # In production, we might want to check if cases count == 0
        SampleDataService.generate_sample_data(db, firm.id, current_user.id)

    db.commit()
    
    return {"status": "success", "message": "Onboarding completed successfully"}
