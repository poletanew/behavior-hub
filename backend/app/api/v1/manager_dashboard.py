import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.manager_dashboard import FinancialOutlookResponse, ManagerDashboardResponse, ProgramPerformanceResponse
from app.services import manager_dashboard_service, program_performance_service

router = APIRouter(prefix="/clinic/manager-dashboard", tags=["manager-dashboard"])


@router.get("", response_model=ManagerDashboardResponse)
def get_manager_dashboard(
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 29.5 — visão de negócio da clínica (somente administrador da clínica).
    Sem filtros, o período padrão é o mês corrente."""
    return manager_dashboard_service.get_manager_dashboard(db, user, date_from=date_from, date_to=date_to)


@router.get("/program-performance", response_model=list[ProgramPerformanceResponse])
def get_program_performance(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Addendum v3.0, RF-32 — desempenho agregado por treino da Training Library."""
    return program_performance_service.get_program_performance(db, user)


@router.get("/financial-outlook", response_model=FinancialOutlookResponse)
def get_financial_outlook(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Addendum v3.0, RF-32 — previsibilidade financeira da própria assinatura."""
    return manager_dashboard_service.get_financial_outlook(db, user)
