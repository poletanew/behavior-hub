import datetime
import uuid

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    before: dict | None
    after: dict | None
    timestamp: datetime.datetime

    class Config:
        from_attributes = True
