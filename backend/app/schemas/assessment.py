import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import AssessmentProtocol, TreatmentArea


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


class PlanDraftItem(BaseModel):
    """RF-06 — um objetivo sugerido a partir de um domínio de menor desempenho;
    sempre editável antes de virar um Objective real via /activate-plan-draft."""

    area: TreatmentArea
    domain_code: str
    domain_label: str
    normalized_pct: float
    title: str
    description: str
    criteria: str
    strategies: str


class AssessmentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    protocol: AssessmentProtocol
    applied_date: datetime.date
    raw_scores: list[DomainScoreResponse]
    summary: str | None
    created_at: datetime.datetime
    ai_generated_plan_draft: list[PlanDraftItem] = Field(default_factory=list)
    plan_draft_activated_at: datetime.datetime | None

    class Config:
        from_attributes = True


class ActivatePlanDraftRequest(BaseModel):
    items: list[PlanDraftItem] = Field(min_length=1)


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
    values_by_date: dict[str, float]
    gain_absolute_pp: float
    gain_relative_pct: float | None


class AssessmentComparisonResponse(BaseModel):
    protocol: AssessmentProtocol
    assessment_ids: list[uuid.UUID]
    applied_dates: list[datetime.date]
    domains: list[DomainComparisonPoint]
    interpretive_summary: str


class SuggestedTrainingRef(BaseModel):
    training_id: uuid.UUID
    title: str
    objective: str


class SuggestedTrainingFolderEntry(BaseModel):
    """Addendum v3.0, RF-36 — um domínio de menor desempenho desta avaliação e os
    treinos da Training Library que já existem no sistema e parecem relevantes
    a ele; nenhum vínculo é criado aqui, é só a sugestão para revisão."""

    domain_code: str
    domain_label: str
    normalized_pct: float
    trainings: list[SuggestedTrainingRef]
