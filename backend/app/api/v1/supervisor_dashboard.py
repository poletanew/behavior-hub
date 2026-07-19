from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.supervisor_dashboard import SupervisorDashboardResponse
from app.services import supervisor_dashboard_service

router = APIRouter(prefix="/clinic/supervisor-dashboard", tags=["supervisor-dashboard"])


@router.get("", response_model=SupervisorDashboardResponse)
def get_supervisor_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 29.4 — painel consolidado por equipe (somente admin/supervisor de clínica)."""
    return supervisor_dashboard_service.get_supervisor_dashboard(db, user)
