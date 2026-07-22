import datetime
import uuid

from pydantic import BaseModel, Field


class ReinforcerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    effectiveness_notes: str | None = None


class ReinforcerResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    name: str
    effectiveness_notes: str | None
    usage_count: int = 0

    class Config:
        from_attributes = True


class SessionReinforcerCreateRequest(BaseModel):
    reinforcer_id: uuid.UUID
    effectiveness_note: str | None = None


class SessionReinforcerResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    reinforcer_id: uuid.UUID
    reinforcer_name: str
    effectiveness_note: str | None
    used_at: datetime.datetime

    class Config:
        from_attributes = True
