import datetime
import uuid

from pydantic import BaseModel, model_validator

from app.models.enums import AppointmentStatus, CancellationReason


class AppointmentCreateRequest(BaseModel):
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    scheduled_start: datetime.datetime
    scheduled_end: datetime.datetime
    notes: str | None = None

    @model_validator(mode="after")
    def _check_range(self) -> "AppointmentCreateRequest":
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end must be after scheduled_start")
        return self


class AppointmentUpdateRequest(BaseModel):
    professional_id: uuid.UUID | None = None
    scheduled_start: datetime.datetime | None = None
    scheduled_end: datetime.datetime | None = None
    notes: str | None = None


class AppointmentStatusChangeRequest(BaseModel):
    reason: CancellationReason | None = None
    notes: str | None = None


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    professional_id: uuid.UUID
    professional_name: str
    scheduled_start: datetime.datetime
    scheduled_end: datetime.datetime
    status: AppointmentStatus
    cancellation_reason: CancellationReason | None
    status_notes: str | None
    notes: str | None
    session_id: uuid.UUID | None
    deleted_at: datetime.datetime | None
    created_at: datetime.datetime


class AttendanceRateResponse(BaseModel):
    patient_id: uuid.UUID
    completed_count: int
    no_show_count: int
    attendance_rate_pct: float | None
