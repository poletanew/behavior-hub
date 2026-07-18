import datetime

from pydantic import BaseModel


class ManagerDashboardResponse(BaseModel):
    period_start: datetime.date
    period_end: datetime.date
    active_patients_count: int
    active_professionals_count: int
    sessions_count: int
    clinical_hours: float
    occupancy_rate_pct: float | None
