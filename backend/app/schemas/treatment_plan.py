import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import ObjectivePriority, ObjectiveStatus, TreatmentArea


class ObjectiveCreateRequest(BaseModel):
    area: TreatmentArea
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    criteria: str | None = None
    strategies: str | None = None
    priority: ObjectivePriority = ObjectivePriority.MEDIUM
    training_ids: list[uuid.UUID] = Field(default_factory=list)
    force: bool = False


class ObjectiveUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    criteria: str | None = None
    strategies: str | None = None
    status: ObjectiveStatus | None = None
    priority: ObjectivePriority | None = None


class DuplicateCandidate(BaseModel):
    id: uuid.UUID
    title: str
    area: TreatmentArea
    status: ObjectiveStatus
    author_id: uuid.UUID
    similarity: float


class ObjectiveResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    area: TreatmentArea
    title: str
    description: str | None
    criteria: str | None
    strategies: str | None
    status: ObjectiveStatus
    priority: ObjectivePriority
    author_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    deleted_at: datetime.datetime | None
    training_ids: list[uuid.UUID] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TreatmentPlanResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    version: int
    objectives: list[ObjectiveResponse]

    class Config:
        from_attributes = True


class ObjectiveCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1)
    mentioned_user_id: uuid.UUID | None = None


class ObjectiveCommentResponse(BaseModel):
    id: uuid.UUID
    objective_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ObjectiveHistoryEntry(BaseModel):
    action: str
    actor_user_id: uuid.UUID | None
    before: dict | None
    after: dict | None
    timestamp: datetime.datetime

    class Config:
        from_attributes = True
