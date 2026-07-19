import datetime
import uuid

from pydantic import BaseModel, Field, model_validator


class ResourceLinkCreateRequest(BaseModel):
    resource_id: uuid.UUID
    training_id: uuid.UUID | None = None
    objective_id: uuid.UUID | None = None
    relevance_score: int = Field(default=3, ge=1, le=5)

    @model_validator(mode="after")
    def check_single_target(self):
        if (self.training_id is None) == (self.objective_id is None):
            raise ValueError("Exactly one of training_id or objective_id must be set")
        return self


class ResourceLinkResponse(BaseModel):
    id: uuid.UUID
    resource_id: uuid.UUID
    resource_title: str
    resource_type: str
    training_id: uuid.UUID | None
    objective_id: uuid.UUID | None
    relevance_score: int
    created_by_user_id: uuid.UUID
    created_at: datetime.datetime
