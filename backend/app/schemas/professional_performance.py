import uuid
from typing import Literal

from pydantic import BaseModel


class ProfessionalPerformanceResponse(BaseModel):
    """Addendum v3.0, RF-31 — relatório individual por profissional/AT,
    distinto do Painel de Supervisão (Seção 29.4)."""

    professional_id: uuid.UUID
    professional_name: str
    professional_role: str
    sessions_count: int
    registration_consistency_pct: float | None
    average_accuracy_pct: float | None
    procedure_variability_pp: float | None
    applier_efficiency_label: Literal["alta", "media", "baixa"] | None
