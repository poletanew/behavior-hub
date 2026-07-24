import uuid

from pydantic import BaseModel

from app.schemas.session import SessionResponse


class DashboardResponse(BaseModel):
    active_patients_count: int
    sessions_today_count: int
    recent_sessions: list[SessionResponse]


class WorkspaceKpis(BaseModel):
    sessions_count: int
    programs_count: int
    avg_trials_per_session: float
    avg_accuracy_pct: float


class AreaPerformancePoint(BaseModel):
    area: str
    accuracy_pct: float


class TrainingRankingPoint(BaseModel):
    training_id: uuid.UUID
    title: str
    accuracy_pct: float


class ResultDistribution(BaseModel):
    correct: int
    incorrect: int
    partial: int
    no_response: int


class WeeklySessionsPoint(BaseModel):
    week_label: str
    sessions_count: int


class WorkspaceDashboardResponse(BaseModel):
    kpis: WorkspaceKpis
    area_performance: list[AreaPerformancePoint]
    training_ranking: list[TrainingRankingPoint]
    distribution: ResultDistribution
    weekly_sessions: list[WeeklySessionsPoint]
