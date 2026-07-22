import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import PromptLevel, SessionMediaType, TrialResult


class SessionCreateRequest(BaseModel):
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    occurred_at: datetime.datetime
    notes: str | None = None
    photo_url: str | None = None
    training_ids: list[uuid.UUID] = Field(default_factory=list)
    appointment_id: uuid.UUID | None = None


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
    media_type: SessionMediaType | None
    media_duration_seconds: int | None
    deleted_at: datetime.datetime | None
    trainings: list[SessionTrainingResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SessionMediaUrlResponse(BaseModel):
    """Addendum v3.0, RF-20 — URL assinada e temporária (Seção 17.2) para
    visualizar a foto/vídeo anexado à sessão."""

    media_type: SessionMediaType
    url: str
    duration_seconds: int | None


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
