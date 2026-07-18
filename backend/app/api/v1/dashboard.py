import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services import patient_service, session_service

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 9 — indicadores derivados de dados reais; conta nova/sem sessoes exibe zero (AC-01/AC-12)."""
    active_patients_count = patient_service.count_active_patients(db, user)
    sessions = session_service.list_sessions(db, user)

    today = datetime.datetime.now(datetime.timezone.utc).date()
    sessions_today_count = sum(1 for s in sessions if s.occurred_at.date() == today)

    return DashboardResponse(
        active_patients_count=active_patients_count,
        sessions_today_count=sessions_today_count,
        recent_sessions=sessions[:10],
    )
