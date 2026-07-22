import datetime
import uuid

from pydantic import BaseModel


class AnamnesisSaveRequest(BaseModel):
    chief_complaint: str | None = None
    birth_history: str | None = None
    developmental_history: str | None = None
    developmental_milestones: str | None = None
    family_history: str | None = None


class AnamnesisResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    created_by_user_id: uuid.UUID
    chief_complaint: str | None
    birth_history: str | None
    developmental_history: str | None
    developmental_milestones: str | None
    family_history: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
