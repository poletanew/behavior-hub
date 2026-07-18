import datetime
import uuid

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    type: str
    message: str
    entity_type: str
    entity_id: uuid.UUID
    read_at: datetime.datetime | None
    created_at: datetime.datetime

    class Config:
        from_attributes = True
