import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import AssessmentProtocol


class DomainScoreInput(BaseModel):
    domain_code: str
    raw_value: float = Field(ge=0)
    max_value: float | None = Field(default=None, gt=0)


class AssessmentCreateRequest(BaseModel):
    protocol: AssessmentProtocol
    applied_date: datetime.date
    domain_scores: list[DomainScoreInput]
    summary: str | None = None


class AssessmentUpdateRequest(BaseModel):
    summary: str | None = None


class DomainScoreResponse(BaseModel):
    domain_code: str
    domain_label: str
    raw_value: float
    max_value: float
    normalized_pct: float


class AssessmentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    protocol: AssessmentProtocol
    applied_date: datetime.date
    raw_scores: list[DomainScoreResponse]
    summary: str | None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ProtocolDomainDefinition(BaseModel):
    domain_code: str
    domain_label: str
    max_value: float | None


class ProtocolDefinitionResponse(BaseModel):
    protocol: AssessmentProtocol
    label: str
    requires_license: bool
    domains: list[ProtocolDomainDefinition]


class DomainComparisonPoint(BaseModel):
    domain_code: str
    domain_label: str
    earliest_pct: float
    latest_pct: float
    gain_absolute_pp: float
    gain_relative_pct: float | None


class AssessmentComparisonResponse(BaseModel):
    protocol: AssessmentProtocol
    assessment_ids: list[uuid.UUID]
    applied_dates: list[datetime.date]
    domains: list[DomainComparisonPoint]
    interpretive_summary: str
