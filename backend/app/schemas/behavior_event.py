import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import BehaviorIntensity


class BehaviorEventCreateRequest(BaseModel):
    session_id: uuid.UUID
    antecedent: str = Field(min_length=1)
    behavior: str = Field(min_length=1)
    consequence: str = Field(min_length=1)
    frequency_count: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    intensity: BehaviorIntensity | None = None
    occurred_at: datetime.datetime | None = None


class BehaviorEventResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    session_id: uuid.UUID
    recorded_by_user_id: uuid.UUID
    antecedent: str
    behavior: str
    consequence: str
    frequency_count: int | None
    duration_seconds: int | None
    intensity: BehaviorIntensity | None
    occurred_at: datetime.datetime

    class Config:
        from_attributes = True
