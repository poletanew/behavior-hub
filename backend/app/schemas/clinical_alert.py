import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import ClinicalAlertType


class ClinicalAlertThresholdsUpdateRequest(BaseModel):
    """Seção 29.1 — limiares configuráveis por clínica, apenas no plano Enterprise."""

    no_collection_days: int | None = Field(default=None, ge=1)
    regression_window_sessions: int | None = Field(default=None, ge=1)
    regression_drop_pp: int | None = Field(default=None, ge=1, le=100)
    stagnation_session_count: int | None = Field(default=None, ge=1)
    stagnation_band_pp: int | None = Field(default=None, ge=1, le=100)
    fading_session_count: int | None = Field(default=None, ge=1)
    fading_independence_pct: int | None = Field(default=None, ge=1, le=100)
    mastery_suggestion_session_count: int | None = Field(default=None, ge=1)
    mastery_suggestion_accuracy_pct: int | None = Field(default=None, ge=1, le=100)


class ClinicalAlertResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    objective_id: uuid.UUID
    objective_title: str
    alert_type: ClinicalAlertType
    message: str
    detail: dict | None
    triggered_at: datetime.datetime
    resolved_at: datetime.datetime | None
