import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ApplierType, GeneralizationContext, ObjectivePriority, ObjectiveStatus, TreatmentArea


class ObjectiveCreateRequest(BaseModel):
    area: TreatmentArea
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    criteria: str | None = None
    strategies: str | None = None
    priority: ObjectivePriority = ObjectivePriority.MEDIUM
    training_ids: list[uuid.UUID] = Field(default_factory=list)
    force: bool = False
    ai_generated: bool = False
    ai_source_document_id: uuid.UUID | None = None
    ai_source_assessment_id: uuid.UUID | None = None


class ObjectiveUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    criteria: str | None = None
    strategies: str | None = None
    status: ObjectiveStatus | None = None
    priority: ObjectivePriority | None = None


class DuplicateCandidate(BaseModel):
    id: uuid.UUID
    title: str
    area: TreatmentArea
    status: ObjectiveStatus
    author_id: uuid.UUID
    similarity: float


class GeneralizationContextEntry(BaseModel):
    """Addendum v3.0, RF-24 — um registro de onde a habilidade dominada já foi
    testada (clínica, casa, escola, outro) e o resultado observado."""

    context: GeneralizationContext
    tested_at: datetime.date
    result: str
    notes: str | None = None


class ObjectiveResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    patient_id: uuid.UUID
    area: TreatmentArea
    title: str
    description: str | None
    criteria: str | None
    strategies: str | None
    status: ObjectiveStatus
    priority: ObjectivePriority
    author_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    deleted_at: datetime.datetime | None
    training_ids: list[uuid.UUID] = Field(default_factory=list)
    ai_generated: bool
    ai_source_document_id: uuid.UUID | None
    ai_source_assessment_id: uuid.UUID | None
    ai_reviewed_at: datetime.datetime | None
    maintenance_check_date: datetime.date | None
    maintenance_due: bool = False
    generalization_contexts: list[GeneralizationContextEntry] = Field(default_factory=list)
    display_order: int = 0

    class Config:
        from_attributes = True


class ObjectiveReorderRequest(BaseModel):
    """Addendum v3.0, RF-28 — arrastar e soltar para reordenar prioridade dos
    objetivos de uma área; a lista deve conter exatamente os objetivos ativos
    dessa área, na nova ordem desejada."""

    area: TreatmentArea
    ordered_ids: list[uuid.UUID] = Field(min_length=1)


class GeneralizationContextCreateRequest(BaseModel):
    context: GeneralizationContext
    tested_at: datetime.date
    result: str = Field(min_length=1)
    notes: str | None = None


class MaintenanceCheckRequest(BaseModel):
    """RF-24 — resultado do reteste periódico de manutenção."""

    result: Literal["mantida", "perdida"]
    notes: str | None = None


class ObjectiveApplierCreateRequest(BaseModel):
    applier_type: ApplierType
    applier_user_id: uuid.UUID


class ObjectiveApplierResponse(BaseModel):
    id: uuid.UUID
    objective_id: uuid.UUID
    applier_type: ApplierType
    applier_user_id: uuid.UUID
    applier_name: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ObjectiveAIFillRequest(BaseModel):
    attachment_id: uuid.UUID


class ObjectiveAIFillResponse(BaseModel):
    """RF-05 — rascunho sugerido a partir do texto extraído do PDF; nunca é
    persistido por esta rota — só vira dado ativo se o profissional revisar e
    clicar em Salvar no formulário de Novo Objetivo."""

    source_document_id: uuid.UUID
    title: str
    description: str
    criteria: str
    strategies: str
    extraction_note: str | None = None


class TreatmentPlanAttachmentResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    area: TreatmentArea
    original_filename: str
    uploaded_by_user_id: uuid.UUID
    uploaded_by_name: str
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True


class TreatmentPlanAttachmentWithUrlResponse(TreatmentPlanAttachmentResponse):
    view_url: str


class TreatmentPlanResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    version: int
    objectives: list[ObjectiveResponse]
    attachments: list[TreatmentPlanAttachmentResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ObjectiveCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1)
    mentioned_user_id: uuid.UUID | None = None


class ObjectiveCommentResponse(BaseModel):
    id: uuid.UUID
    objective_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ObjectiveHistoryEntry(BaseModel):
    action: str
    actor_user_id: uuid.UUID | None
    before: dict | None
    after: dict | None
    timestamp: datetime.datetime

    class Config:
        from_attributes = True
