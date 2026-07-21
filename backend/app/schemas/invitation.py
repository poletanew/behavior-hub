import datetime
import uuid

from pydantic import BaseModel, EmailStr, model_validator

from app.models.enums import InvitationStatus, Specialty, UserType

INVITABLE_ROLES = (UserType.PROFESSIONAL, UserType.SUPERVISOR, UserType.FAMILY, UserType.AT)


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    specialty: Specialty | None = None
    role: UserType = UserType.PROFESSIONAL
    # Seção 29.6 — obrigatório apenas quando role == FAMILY.
    patient_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _patient_id_required_for_family(self) -> "InvitationCreateRequest":
        if self.role == UserType.FAMILY and self.patient_id is None:
            raise ValueError("patient_id is required when role is family")
        if self.role != UserType.FAMILY and self.patient_id is not None:
            raise ValueError("patient_id is only allowed when role is family")
        return self


class InvitationResponse(BaseModel):
    id: uuid.UUID
    email: str
    specialty: Specialty | None
    role: UserType
    patient_id: uuid.UUID | None
    status: InvitationStatus
    expires_at: datetime.datetime
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class InvitationCreatedResponse(InvitationResponse):
    raw_token: str


class InvitationAcceptRequest(BaseModel):
    name: str
    password: str
    accept_terms: bool
