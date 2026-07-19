import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import PaymentStatus


class SessionChargeCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    due_date: datetime.date | None = None
    notes: str | None = None


class SessionChargeUpdateRequest(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    due_date: datetime.date | None = None
    notes: str | None = None


class SessionChargeStatusUpdateRequest(BaseModel):
    payment_status: PaymentStatus


class SessionChargeResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    session_date: datetime.datetime
    amount: float
    due_date: datetime.date | None
    payment_status: PaymentStatus
    paid_at: datetime.datetime | None
    notes: str | None
    created_by_user_id: uuid.UUID
    created_at: datetime.datetime
