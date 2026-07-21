import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ResourceType, ResourceVisibility

AIResourceKind = Literal["historia_social", "rotina_visual", "cartao_comunicacao"]


class ResourceResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    category: str | None
    suggested_age_range: str | None
    resource_type: ResourceType
    original_filename: str
    content_type: str
    size_bytes: int
    visibility: ResourceVisibility
    uploaded_by_user_id: uuid.UUID
    created_at: datetime.datetime
    deleted_at: datetime.datetime | None
    ai_generated: bool
    ai_reviewed_at: datetime.datetime | None

    class Config:
        from_attributes = True


class ResourceWithUrlResponse(ResourceResponse):
    view_url: str


class ResourceAIDraftRequest(BaseModel):
    kind: AIResourceKind
    theme: str = Field(min_length=1, max_length=200)
    age_range: str = Field(min_length=1, max_length=60)


class ResourceAIDraftResponse(BaseModel):
    """RF-12 — rascunho não persistido; só existe nesta resposta até o
    profissional revisar, editar e publicar explicitamente."""

    kind: AIResourceKind
    theme: str
    age_range: str
    title: str
    description: str
    content_text: str


class ResourceAIPublishRequest(BaseModel):
    kind: AIResourceKind
    theme: str
    age_range: str
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    content_text: str = Field(min_length=1)
    category: str | None = None
    visibility: ResourceVisibility = ResourceVisibility.PRIVATE
