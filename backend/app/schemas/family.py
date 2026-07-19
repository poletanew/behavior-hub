import datetime
import uuid

from pydantic import BaseModel

from app.schemas.report import CumulativePoint, LineSeries, RadarPoint


class FamilyAccessResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    family_user_id: uuid.UUID
    family_user_name: str
    family_user_email: str
    granted_by_user_id: uuid.UUID
    consent_given_at: datetime.datetime
    can_view_evolution_charts: bool
    can_view_upcoming_appointments: bool
    can_view_team_guidance: bool
    can_view_home_materials: bool
    can_use_messaging: bool
    revoked_at: datetime.datetime | None
    created_at: datetime.datetime


class FamilyAccessUpdateRequest(BaseModel):
    can_view_evolution_charts: bool | None = None
    can_view_upcoming_appointments: bool | None = None
    can_view_team_guidance: bool | None = None
    can_view_home_materials: bool | None = None
    can_use_messaging: bool | None = None


class FamilyMyAccessResponse(BaseModel):
    patient_id: uuid.UUID
    patient_name: str
    can_view_evolution_charts: bool
    can_view_upcoming_appointments: bool
    can_view_team_guidance: bool
    can_view_home_materials: bool
    can_use_messaging: bool


class FamilyEvolutionResponse(BaseModel):
    line: list[LineSeries]
    radar: list[RadarPoint]
    cumulative: list[CumulativePoint]


class FamilyAppointmentResponse(BaseModel):
    id: uuid.UUID
    professional_name: str
    scheduled_start: datetime.datetime
    scheduled_end: datetime.datetime
    status: str


class FamilyGuidanceResponse(BaseModel):
    id: uuid.UUID
    period_start: datetime.date
    period_end: datetime.date
    content: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class FamilyMessageCreateRequest(BaseModel):
    body: str


class FamilyMessageResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    sender_user_id: uuid.UUID
    sender_name: str
    body: str
    created_at: datetime.datetime
