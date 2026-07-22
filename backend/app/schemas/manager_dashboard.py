import datetime
import uuid
from typing import Literal

from pydantic import BaseModel

from app.models.enums import SubscriptionPlan, SubscriptionStatus


class ManagerDashboardResponse(BaseModel):
    period_start: datetime.date
    period_end: datetime.date
    active_patients_count: int
    active_professionals_count: int
    sessions_count: int
    clinical_hours: float
    occupancy_rate_pct: float | None


class ProgramPerformanceResponse(BaseModel):
    """Addendum v3.0, RF-32 — desempenho agregado por treino da Training
    Library, restrito a treinos com pelo menos 2 pacientes distintos."""

    training_id: uuid.UUID
    training_title: str
    patients_count: int
    objectives_count: int
    mastery_rate_pct: float
    average_days_to_mastery: float | None


class FinancialOutlookResponse(BaseModel):
    """Addendum v3.0, RF-32 — previsibilidade financeira usando os dados de
    assinatura já existentes (Seção 8.3, Fase 3); ver backend/README.md
    sobre o porquê do escopo ser por clínica, não por plataforma."""

    subscription_plan: SubscriptionPlan
    subscription_status: SubscriptionStatus
    current_period_end: datetime.datetime | None
    days_until_renewal: int | None
    churn_risk_label: Literal["baixo", "alto", "assinatura_encerrada", "nao_aplicavel"]
