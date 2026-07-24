import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import TrainingLinkStatus, TrainingVisibility


class TrainingCategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None

    class Config:
        from_attributes = True


class TrainingCreateRequest(BaseModel):
    category_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    objective: str
    discriminative_instruction: str | None = None
    expected_response: str | None = None
    prompt_hierarchy: str | None = None
    mastery_criteria: str | None = None
    notes: str | None = None
    suggested_age_range: str | None = None
    ai_generated: bool = False


class TrainingResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    title: str
    objective: str
    discriminative_instruction: str | None
    expected_response: str | None
    prompt_hierarchy: str | None
    mastery_criteria: str | None
    notes: str | None
    suggested_age_range: str | None
    visibility: TrainingVisibility
    ai_generated: bool

    class Config:
        from_attributes = True


class TrainingAIFillRequest(BaseModel):
    category_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)


class TrainingAIFillResponse(BaseModel):
    objective: str
    discriminative_instruction: str
    expected_response: str
    prompt_hierarchy: str
    mastery_criteria: str


class TrainingPatientLinkCreateRequest(BaseModel):
    patient_id: uuid.UUID


class TrainingPatientLinkResponse(BaseModel):
    id: uuid.UUID
    training_id: uuid.UUID
    training_title: str
    patient_id: uuid.UUID
    status: TrainingLinkStatus
    linked_by_user_id: uuid.UUID
    linked_at: datetime.datetime

    class Config:
        from_attributes = True
