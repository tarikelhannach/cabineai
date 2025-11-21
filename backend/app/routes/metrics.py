from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Expediente, Document, User, AuditLog, CaseStatus, UserRole
from ..auth.jwt import get_current_user, require_role

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    responses={404: {"description": "Not found"}},
)

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_metrics(
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Get aggregated metrics for the admin dashboard.
    Only accessible by admins.
    """
    
    # 1. KPI Counts
    total_cases = db.query(Expediente).filter(Expediente.firm_id == current_user.firm_id).count()
    active_cases = db.query(Expediente).filter(
        Expediente.firm_id == current_user.firm_id,
        Expediente.status.in_([CaseStatus.PENDING, CaseStatus.IN_PROGRESS])
    ).count()
    total_documents = db.query(Document).filter(Document.firm_id == current_user.firm_id).count()
    total_users = db.query(User).filter(User.firm_id == current_user.firm_id).count()

    # 2. Cases by Status (for Pie Chart)
    cases_by_status_query = db.query(
        Expediente.status, func.count(Expediente.id)
    ).filter(
        Expediente.firm_id == current_user.firm_id
    ).group_by(Expediente.status).all()
    
    cases_by_status = [
        {"name": status.value, "value": count} 
        for status, count in cases_by_status_query
    ]

    # 3. Recent Activity (Last 5 Audit Logs)
    recent_activity_query = db.query(AuditLog).filter(
        AuditLog.firm_id == current_user.firm_id
    ).order_by(AuditLog.timestamp.desc()).limit(5).all()
    
    recent_activity = [
        {
            "action": log.action,
            "user": log.user.full_name if log.user else "System",
            "timestamp": log.timestamp.isoformat(),
            "details": log.details
        }
        for log in recent_activity_query
    ]

    # 4. Documents Uploaded (Last 30 Days) - Mock data for now if no real time series data is easy to query quickly
    # In a real scenario, we would group by date.
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    docs_query = db.query(
        func.date(Document.created_at).label('date'), 
        func.count(Document.id)
    ).filter(
        Document.firm_id == current_user.firm_id,
        Document.created_at >= start_date
    ).group_by('date').all()
    
    documents_trend = [
        {"date": str(day), "count": count} 
        for day, count in docs_query
    ]

    return {
        "kpi": {
            "total_cases": total_cases,
            "active_cases": active_cases,
            "total_documents": total_documents,
            "total_users": total_users
        },
        "charts": {
            "cases_by_status": cases_by_status,
            "documents_trend": documents_trend
        },
        "recent_activity": recent_activity
    }
