import datetime
import uuid

from pydantic import BaseModel


class ATPatientResponse(BaseModel):
    id: uuid.UUID
    name: str
    birth_date: datetime.date

    class Config:
        from_attributes = True


class ATApplyTrainingRequest(BaseModel):
    training_id: uuid.UUID
    occurred_at: datetime.datetime
    notes: str | None = None
