import datetime
import uuid

from pydantic import BaseModel, EmailStr

from app.models.enums import InvitationStatus, Specialty


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    specialty: Specialty | None = None


class InvitationResponse(BaseModel):
    id: uuid.UUID
    email: str
    specialty: Specialty | None
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
