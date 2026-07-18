import datetime
import uuid
from typing import Literal

from pydantic import BaseModel

EntityType = Literal["patient", "objective", "resource", "appointment"]


class DeletedItemResponse(BaseModel):
    entity_type: EntityType
    id: uuid.UUID
    label: str
    deleted_at: datetime.datetime
    deleted_by: uuid.UUID | None
    days_remaining: int
