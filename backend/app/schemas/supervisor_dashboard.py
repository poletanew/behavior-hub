import uuid

from pydantic import BaseModel


class SupervisorDashboardTherapistRow(BaseModel):
    professional_id: uuid.UUID
    professional_name: str
    assigned_patients_count: int
    completed_sessions_count: int
    no_show_count: int
    session_completion_pct: float | None
    active_objectives_count: int
    treatment_plan_adherence_pct: float | None
    low_adherence_alert: bool
    no_recent_registration_alert: bool


class SupervisorDashboardResponse(BaseModel):
    therapists: list[SupervisorDashboardTherapistRow]
