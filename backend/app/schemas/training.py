import uuid

from pydantic import BaseModel, Field

from app.models.enums import TrainingVisibility


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

    class Config:
        from_attributes = True
