import datetime
import uuid

from pydantic import BaseModel, Field


class SessionTemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    patient_id: uuid.UUID | None = None
    training_ids: list[uuid.UUID] = Field(min_length=1)


class SaveAsTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SessionTemplateTrainingResponse(BaseModel):
    training_id: uuid.UUID
    sequence: int

    class Config:
        from_attributes = True


class SessionTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    patient_id: uuid.UUID | None
    created_by_user_id: uuid.UUID
    created_at: datetime.datetime
    trainings: list[SessionTemplateTrainingResponse]

    class Config:
        from_attributes = True


class SessionFromTemplateRequest(BaseModel):
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    occurred_at: datetime.datetime
    notes: str | None = None


class DuplicateSessionRequest(BaseModel):
    occurred_at: datetime.datetime
    professional_id: uuid.UUID | None = None
    notes: str | None = None
