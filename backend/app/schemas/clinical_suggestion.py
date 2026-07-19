import datetime
import uuid

from pydantic import BaseModel

from app.models.enums import SuggestionStatus, SuggestionType


class ClinicalSuggestionResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    objective_id: uuid.UUID | None
    objective_title: str | None
    training_id: uuid.UUID | None
    training_title: str | None
    suggestion_type: SuggestionType
    message: str
    detail: dict | None
    status: SuggestionStatus
    created_at: datetime.datetime
    decided_at: datetime.datetime | None
