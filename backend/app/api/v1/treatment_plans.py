import datetime
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ObjectivePriority, ObjectiveStatus, TreatmentArea
from app.models.treatment_plan import Objective, TreatmentPlan, TreatmentPlanAttachment
from app.models.user import User
from app.schemas.treatment_plan import (
    GeneralizationContextCreateRequest,
    MaintenanceCheckRequest,
    ObjectiveAIFillRequest,
    ObjectiveAIFillResponse,
    ObjectiveApplierCreateRequest,
    ObjectiveApplierResponse,
    ObjectiveCommentCreateRequest,
    ObjectiveCommentResponse,
    ObjectiveCreateRequest,
    ObjectiveHistoryEntry,
    ObjectiveReorderRequest,
    ObjectiveResponse,
    ObjectiveUpdateRequest,
    TreatmentPlanAttachmentResponse,
    TreatmentPlanAttachmentWithUrlResponse,
    TreatmentPlanResponse,
)
from app.services import patient_service, treatment_plan_service

router = APIRouter(tags=["treatment-plans"])


def _to_attachment_response(db: Session, attachment: TreatmentPlanAttachment) -> TreatmentPlanAttachmentResponse:
    uploader = db.get(User, attachment.uploaded_by_user_id)
    return TreatmentPlanAttachmentResponse(
        id=attachment.id,
        plan_id=attachment.plan_id,
        area=attachment.area,
        original_filename=attachment.original_filename,
        uploaded_by_user_id=attachment.uploaded_by_user_id,
        uploaded_by_name=uploader.name if uploader else "Usuário removido",
        uploaded_at=attachment.uploaded_at,
    )


def _to_objective_response(db: Session, objective: Objective) -> ObjectiveResponse:
    plan = db.get(TreatmentPlan, objective.plan_id)
    maintenance_due = (
        objective.maintenance_check_date is not None and objective.maintenance_check_date <= datetime.date.today()
    )
    return ObjectiveResponse(
        id=objective.id,
        plan_id=objective.plan_id,
        patient_id=plan.patient_id,
        area=objective.area,
        title=objective.title,
        description=objective.description,
        criteria=objective.criteria,
        strategies=objective.strategies,
        status=objective.status,
        priority=objective.priority,
        author_id=objective.author_id,
        created_at=objective.created_at,
        updated_at=objective.updated_at,
        deleted_at=objective.deleted_at,
        training_ids=treatment_plan_service.get_objective_training_ids(db, objective.id),
        ai_generated=objective.ai_generated,
        ai_source_document_id=objective.ai_source_document_id,
        ai_source_assessment_id=objective.ai_source_assessment_id,
        ai_reviewed_at=objective.ai_reviewed_at,
        maintenance_check_date=objective.maintenance_check_date,
        maintenance_due=maintenance_due,
        generalization_contexts=objective.generalization_contexts or [],
        display_order=objective.display_order,
    )


@router.get("/patients/{patient_id}/treatment-plan", response_model=TreatmentPlanResponse)
def get_treatment_plan(
    patient_id: uuid.UUID,
    area: TreatmentArea | None = None,
    status_filter: ObjectiveStatus | None = Query(default=None, alias="status"),
    priority: ObjectivePriority | None = None,
    professional_id: uuid.UUID | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 13.1 — grade multidisciplinar única por paciente, com filtros."""
    patient_service.assert_full_clinical_access(user)
    plan, objectives = treatment_plan_service.get_treatment_plan(
        db,
        user,
        patient_id,
        area=area,
        obj_status=status_filter,
        priority=priority,
        professional_id=professional_id,
        date_from=date_from,
        date_to=date_to,
    )
    return TreatmentPlanResponse(
        id=plan.id,
        patient_id=plan.patient_id,
        version=plan.version,
        objectives=[_to_objective_response(db, o) for o in objectives],
        attachments=[_to_attachment_response(db, a) for a in treatment_plan_service.list_attachments(db, plan.id)],
    )


@router.post(
    "/patients/{patient_id}/treatment-plan/attachments",
    response_model=TreatmentPlanAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    patient_id: uuid.UUID,
    area: TreatmentArea = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """RF-04 — importar um PDF anexado a uma área específica da grade multidisciplinar."""
    attachment = await treatment_plan_service.upload_attachment(db, user, patient_id, area, file)
    return _to_attachment_response(db, attachment)


@router.get("/treatment-plan/attachments/{attachment_id}", response_model=TreatmentPlanAttachmentWithUrlResponse)
def get_attachment(attachment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 15/17.2 — abre com URL temporária e assinada, mesmo visualizador seguro dos Recursos Terapêuticos."""
    patient_service.assert_full_clinical_access(user)
    _patient, attachment = treatment_plan_service.get_attachment_or_404(db, user, attachment_id)
    view_url = treatment_plan_service.get_attachment_view_url(attachment)
    return TreatmentPlanAttachmentWithUrlResponse(
        **_to_attachment_response(db, attachment).model_dump(), view_url=view_url
    )


@router.post(
    "/patients/{patient_id}/treatment-plan/objectives/ai-fill",
    response_model=ObjectiveAIFillResponse,
)
def ai_fill_objective(
    patient_id: uuid.UUID,
    payload: ObjectiveAIFillRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """RF-05 — "Preencher com IA": extrai o texto do PDF já anexado à área (RF-04) e
    sugere título/descrição/estratégias/critério de domínio como rascunho editável."""
    return treatment_plan_service.generate_objective_draft_from_attachment(db, user, patient_id, payload.attachment_id)


@router.post(
    "/patients/{patient_id}/treatment-plan/objectives",
    response_model=ObjectiveResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_objective(
    patient_id: uuid.UUID,
    payload: ObjectiveCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 13.2 — AC-08: objetivo semelhante gera alerta (HTTP 409) com autor e área,
    a menos que `force=true` seja enviado."""
    objective = treatment_plan_service.create_objective(db, user, patient_id, payload)
    return _to_objective_response(db, objective)


@router.post("/patients/{patient_id}/treatment-plan/objectives/reorder", response_model=list[ObjectiveResponse])
def reorder_objectives(
    patient_id: uuid.UUID,
    payload: ObjectiveReorderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v3.0, RF-28 — arrastar e soltar para reordenar prioridade dos objetivos de uma área."""
    objectives = treatment_plan_service.reorder_objectives(db, user, patient_id, payload)
    return [_to_objective_response(db, o) for o in objectives]


@router.get("/objectives/{objective_id}", response_model=ObjectiveResponse)
def get_objective(objective_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Usado para resolver a origem de uma notificação (Seção 32.6)."""
    _patient, objective = treatment_plan_service.get_objective(db, user, objective_id)
    return _to_objective_response(db, objective)


@router.patch("/objectives/{objective_id}", response_model=ObjectiveResponse)
def update_objective(
    objective_id: uuid.UUID,
    payload: ObjectiveUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    objective = treatment_plan_service.update_objective(db, user, objective_id, payload)
    return _to_objective_response(db, objective)


@router.delete("/objectives/{objective_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_objective(objective_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    treatment_plan_service.soft_delete_objective(db, user, objective_id)


@router.post("/objectives/{objective_id}/restore", response_model=ObjectiveResponse)
def restore_objective(objective_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    objective = treatment_plan_service.restore_objective(db, user, objective_id)
    return _to_objective_response(db, objective)


@router.post(
    "/objectives/{objective_id}/comments",
    response_model=ObjectiveCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    objective_id: uuid.UUID,
    payload: ObjectiveCommentCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return treatment_plan_service.add_comment(db, user, objective_id, payload.body, payload.mentioned_user_id)


@router.get("/objectives/{objective_id}/comments", response_model=list[ObjectiveCommentResponse])
def list_comments(objective_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return treatment_plan_service.list_comments(db, user, objective_id)


@router.get("/objectives/{objective_id}/history", response_model=list[ObjectiveHistoryEntry])
def get_history(objective_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return treatment_plan_service.get_history(db, user, objective_id)


@router.post("/objectives/{objective_id}/generalization-contexts", response_model=ObjectiveResponse)
def record_generalization_context(
    objective_id: uuid.UUID,
    payload: GeneralizationContextCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v3.0, RF-24 — registrar onde a generalização de um alvo dominado já foi testada."""
    objective = treatment_plan_service.record_generalization_context(db, user, objective_id, payload)
    return _to_objective_response(db, objective)


@router.post("/objectives/{objective_id}/maintenance-checks", response_model=ObjectiveResponse)
def record_maintenance_check(
    objective_id: uuid.UUID,
    payload: MaintenanceCheckRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v3.0, RF-24 — registra o reteste de manutenção e reagenda o próximo lembrete."""
    objective = treatment_plan_service.record_maintenance_check(db, user, objective_id, payload)
    return _to_objective_response(db, objective)


@router.post(
    "/objectives/{objective_id}/appliers", response_model=ObjectiveApplierResponse, status_code=status.HTTP_201_CREATED
)
def add_applier(
    objective_id: uuid.UUID,
    payload: ObjectiveApplierCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v3.0, RF-25 — marcar um pai/cuidador (ou profissional) como aplicador de um objetivo."""
    return treatment_plan_service.add_applier(db, user, objective_id, payload)


@router.get("/objectives/{objective_id}/appliers", response_model=list[ObjectiveApplierResponse])
def list_appliers(objective_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return treatment_plan_service.list_appliers(db, user, objective_id)
