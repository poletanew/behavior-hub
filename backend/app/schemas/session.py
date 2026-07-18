import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import PromptLevel, TrialResult


class SessionCreateRequest(BaseModel):
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    occurred_at: datetime.datetime
    notes: str | None = None
    photo_url: str | None = None
    training_ids: list[uuid.UUID] = Field(default_factory=list)


class SessionTrainingResponse(BaseModel):
    id: uuid.UUID
    training_id: uuid.UUID
    sequence: int

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    occurred_at: datetime.datetime
    notes: str | None
    photo_url: str | None
    deleted_at: datetime.datetime | None
    trainings: list[SessionTrainingResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AddTrainingsRequest(BaseModel):
    training_ids: list[uuid.UUID] = Field(min_length=1)


class TrialCreateRequest(BaseModel):
    result: TrialResult
    prompt_level: PromptLevel
    notes: str | None = None
    recorded_at: datetime.datetime | None = None


class TrialUpdateRequest(BaseModel):
    result: TrialResult | None = None
    prompt_level: PromptLevel | None = None
    notes: str | None = None


class TrialResponse(BaseModel):
    id: uuid.UUID
    session_training_id: uuid.UUID
    attempt_number: int
    result: TrialResult
    prompt_level: PromptLevel
    notes: str | None
    recorded_at: datetime.datetime
    deleted_at: datetime.datetime | None

    class Config:
        from_attributes = True


class SessionTrainingProgressResponse(BaseModel):
    session_training_id: uuid.UUID
    training_id: uuid.UUID
    trials: list[TrialResponse]
    accuracy_pct: float | None
    independence_pct: float | None
