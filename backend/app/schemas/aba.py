import datetime
import uuid

from pydantic import BaseModel

from app.models.enums import PromptLevel, TrialResult


class ATSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    supervisor_id: uuid.UUID | None
    assigned_patient_count: int


class ABAAssignedPatientResponse(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class ABATrialReviewEntry(BaseModel):
    trial_id: uuid.UUID
    at_user_id: uuid.UUID
    at_name: str
    patient_id: uuid.UUID
    patient_name: str
    training_id: uuid.UUID
    training_title: str
    result: TrialResult
    prompt_level: PromptLevel
    recorded_at: datetime.datetime
