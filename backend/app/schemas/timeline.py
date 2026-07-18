import datetime
import uuid

from pydantic import BaseModel


class TimelineEntryResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    occurred_at: datetime.datetime
    label: str
    source_type: str
    source_id: uuid.UUID
