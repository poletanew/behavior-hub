import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import AssignmentPermission, PatientStatus


class PatientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    birth_date: datetime.date
    guardian_name: str | None = None
    diagnosis: str | None = None
    notes: str | None = None


class PatientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    birth_date: datetime.date | None = None
    guardian_name: str | None = None
    diagnosis: str | None = None
    notes: str | None = None
    status: PatientStatus | None = None


class PatientResponse(BaseModel):
    id: uuid.UUID
    name: str
    birth_date: datetime.date
    guardian_name: str | None
    diagnosis: str | None
    notes: str | None
    photo_url: str | None
    status: PatientStatus
    clinic_id: uuid.UUID | None
    individual_owner_id: uuid.UUID | None
    deleted_at: datetime.datetime | None

    class Config:
        from_attributes = True


class PatientAssignmentCreateRequest(BaseModel):
    professional_id: uuid.UUID
    permission: AssignmentPermission = AssignmentPermission.EDIT_SESSIONS


class PatientAssignmentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    permission: AssignmentPermission

    class Config:
        from_attributes = True


class PatientRestoreResponse(BaseModel):
    id: uuid.UUID
    restored: bool
