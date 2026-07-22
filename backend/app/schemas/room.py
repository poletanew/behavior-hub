import datetime
import uuid

from pydantic import BaseModel, Field


class RoomCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class RoomResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
