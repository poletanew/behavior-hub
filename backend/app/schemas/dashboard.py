from pydantic import BaseModel

from app.schemas.session import SessionResponse


class DashboardResponse(BaseModel):
    active_patients_count: int
    sessions_today_count: int
    recent_sessions: list[SessionResponse]
