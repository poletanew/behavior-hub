import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import WaitlistStatus


class WaitlistEntryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    birth_date: datetime.date | None = None
    guardian_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    notes: str | None = None


class WaitlistEntryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    birth_date: datetime.date | None = None
    guardian_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    notes: str | None = None


class WaitlistConvertRequest(BaseModel):
    """Seção 32.11 — "conversão em paciente completo sem redigitação": só pede
    o que ainda falta (birth_date, se a triagem não tinha capturado)."""

    birth_date: datetime.date | None = None
    diagnosis: str | None = None


class WaitlistEntryResponse(BaseModel):
    id: uuid.UUID
    name: str
    birth_date: datetime.date | None
    guardian_name: str | None
    contact_phone: str | None
    contact_email: str | None
    notes: str | None
    status: WaitlistStatus
    converted_patient_id: uuid.UUID | None
    created_by_user_id: uuid.UUID
    created_at: datetime.datetime

    class Config:
        from_attributes = True
