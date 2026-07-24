import datetime
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, WorkspaceDashboardResponse
from app.services import patient_service, session_service, workspace_dashboard_service

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


@router.get("/dashboard/workspace", response_model=WorkspaceDashboardResponse)
def get_workspace_dashboard(
    patient_id: uuid.UUID | None = Query(default=None),
    professional_id: uuid.UUID | None = Query(default=None),
    date_from: datetime.date | None = Query(default=None),
    date_to: datetime.date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Área de Trabalho (RF-02) — painel do Paciente/Profissional com filtros e
    4 gráficos, tudo calculado em tempo real a partir das sessões e tentativas
    já registradas (nunca dados fixos/ilustrativos)."""
    return workspace_dashboard_service.get_workspace_dashboard(
        db, user, patient_id=patient_id, professional_id=professional_id, date_from=date_from, date_to=date_to
    )
