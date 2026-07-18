import datetime
import uuid

from pydantic import BaseModel

from app.models.enums import ResourceType, ResourceVisibility


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

    class Config:
        from_attributes = True


class ResourceWithUrlResponse(ResourceResponse):
    view_url: str
