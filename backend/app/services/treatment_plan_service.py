import datetime
import io
import uuid

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import (
    SPECIALTY_TO_AREA,
    AssignmentPermission,
    ObjectivePriority,
    ObjectiveStatus,
    TreatmentArea,
    UserType,
)
from app.models.patient import Patient, PatientAssignment
from app.models.training import Training
from app.models.treatment_plan import Objective, ObjectiveComment, ObjectiveTraining, TreatmentPlan, TreatmentPlanAttachment
from app.models.user import User
from app.schemas.treatment_plan import ObjectiveAIFillResponse, ObjectiveCreateRequest, ObjectiveUpdateRequest
from app.services import audit_service, file_service, notification_service, patient_service, rbac_service

DUPLICATE_SIMILARITY_THRESHOLD = 0.35


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def get_or_create_plan(db: Session, patient: Patient) -> TreatmentPlan:
    """Seção 13.1 — cada paciente possui uma página única de Treatment Plan."""
    plan = db.query(TreatmentPlan).filter(TreatmentPlan.patient_id == patient.id).first()
    if plan is None:
        plan = TreatmentPlan(patient_id=patient.id)
        db.add(plan)
        db.commit()
        db.refresh(plan)
    return plan


def _assignment_for(db: Session, patient: Patient, user: User) -> PatientAssignment | None:
    return (
        db.query(PatientAssignment)
        .filter(PatientAssignment.patient_id == patient.id, PatientAssignment.professional_id == user.id)
        .first()
    )


def can_edit_area(db: Session, user: User, patient: Patient, area: TreatmentArea) -> bool:
    """Seção 13.3/17.1 — cada profissional edita objetivos da própria área ou aqueles
    para os quais recebeu permissão (aqui: vínculo FULL_ACCESS). "Editar objetivo de
    outra área" é Configurável para admin de clínica e supervisor."""
    if user.user_type == UserType.INDIVIDUAL:
        return True
    if user.user_type in (UserType.CLINIC_ADMIN, UserType.SUPERVISOR):
        return rbac_service.can_edit_any_objective_area(db, user)

    assignment = _assignment_for(db, patient, user)
    if assignment is None:
        return False
    if assignment.permission == AssignmentPermission.FULL_ACCESS:
        return True
    if assignment.permission == AssignmentPermission.EDIT_AREA_PLAN:
        return SPECIALTY_TO_AREA.get(user.specialty) == area
    return False


def get_treatment_plan(
    db: Session,
    user: User,
    patient_id: uuid.UUID,
    *,
    area: TreatmentArea | None = None,
    obj_status: ObjectiveStatus | None = None,
    priority: ObjectivePriority | None = None,
    professional_id: uuid.UUID | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> tuple[TreatmentPlan, list[Objective]]:
    """Seção 13.1 — filtros por área, status, prioridade, profissional e período."""
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    plan = get_or_create_plan(db, patient)

    query = db.query(Objective).filter(Objective.plan_id == plan.id, Objective.deleted_at.is_(None))
    if area is not None:
        query = query.filter(Objective.area == area)
    if obj_status is not None:
        query = query.filter(Objective.status == obj_status)
    if priority is not None:
        query = query.filter(Objective.priority == priority)
    if professional_id is not None:
        query = query.filter(Objective.author_id == professional_id)
    if date_from is not None:
        query = query.filter(Objective.created_at >= date_from)
    if date_to is not None:
        query = query.filter(Objective.created_at <= date_to)

    objectives = query.order_by(Objective.area, Objective.created_at).all()
    return plan, objectives


def find_duplicate_candidates(db: Session, plan: TreatmentPlan, title: str) -> list[dict]:
    """Seção 13.2 — normalização de texto + trigramas (pg_trgm) para detectar
    objetivos iguais ou semelhantes no mesmo paciente."""
    normalized_title = _normalize(title)
    similarity_expr = func.similarity(Objective.title, title)

    rows = (
        db.query(Objective, similarity_expr.label("score"))
        .filter(Objective.plan_id == plan.id, Objective.deleted_at.is_(None))
        .all()
    )

    candidates = []
    for objective, score in rows:
        is_exact = _normalize(objective.title) == normalized_title
        if is_exact or (score is not None and score >= DUPLICATE_SIMILARITY_THRESHOLD):
            candidates.append(
                {
                    "id": objective.id,
                    "title": objective.title,
                    "area": objective.area,
                    "status": objective.status,
                    "author_id": objective.author_id,
                    "similarity": 1.0 if is_exact else round(float(score), 2),
                }
            )
    candidates.sort(key=lambda c: c["similarity"], reverse=True)
    return candidates


def create_objective(
    db: Session, user: User, patient_id: uuid.UUID, payload: ObjectiveCreateRequest
) -> Objective:
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    plan = get_or_create_plan(db, patient)

    if not can_edit_area(db, user, patient, payload.area):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this area")

    candidates = find_duplicate_candidates(db, plan, payload.title)
    if candidates and not payload.force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Um objetivo semelhante já foi adicionado. Deseja visualizar, mesclar ou continuar?",
                "duplicate_candidates": [
                    {**c, "id": str(c["id"]), "author_id": str(c["author_id"]), "area": c["area"].value, "status": c["status"].value}
                    for c in candidates
                ],
            },
        )

    if payload.ai_source_document_id is not None:
        source_attachment = db.get(TreatmentPlanAttachment, payload.ai_source_document_id)
        if source_attachment is None or source_attachment.plan_id != plan.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source document not found")

    objective = Objective(
        plan_id=plan.id,
        area=payload.area,
        title=payload.title,
        description=payload.description,
        criteria=payload.criteria,
        strategies=payload.strategies,
        priority=payload.priority,
        author_id=user.id,
        ai_generated=payload.ai_generated,
        ai_source_document_id=payload.ai_source_document_id if payload.ai_generated else None,
        # RF-05 — o rascunho gerado por IA só existe em memória no formulário até este
        # exato instante; salvar É a confirmação de revisão humana exigida pela Seção 12.1.
        ai_reviewed_at=datetime.datetime.now(datetime.timezone.utc) if payload.ai_generated else None,
    )
    db.add(objective)
    db.flush()

    for training_id in payload.training_ids:
        if db.get(Training, training_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Training {training_id} not found")
        db.add(ObjectiveTraining(objective_id=objective.id, training_id=training_id))

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="objective_created",
        entity_type="objective",
        entity_id=objective.id,
        after={"title": objective.title, "area": objective.area.value},
    )
    if candidates and payload.force:
        # Seção 13.2 — registrar a decisão quando o usuário continuar apesar do alerta.
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="objective_duplicate_alert_overridden",
            entity_type="objective",
            entity_id=objective.id,
            after={"candidates": [str(c["id"]) for c in candidates]},
        )

    db.commit()
    db.refresh(objective)
    return objective


def _get_objective_or_404(db: Session, user: User, objective_id: uuid.UUID) -> tuple[Patient, Objective]:
    objective = db.get(Objective, objective_id)
    if objective is None or objective.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objective not found")
    plan = db.get(TreatmentPlan, objective.plan_id)
    patient = patient_service.get_patient_or_404(db, user, plan.patient_id)
    return patient, objective


def get_objective(db: Session, user: User, objective_id: uuid.UUID) -> tuple[Patient, Objective]:
    """Usado para resolver a origem de uma notificação (Seção 32.6)."""
    return _get_objective_or_404(db, user, objective_id)


def update_objective(
    db: Session, user: User, objective_id: uuid.UUID, payload: ObjectiveUpdateRequest
) -> Objective:
    patient, objective = _get_objective_or_404(db, user, objective_id)
    if not can_edit_area(db, user, patient, objective.area):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this area")

    before = {
        "title": objective.title,
        "status": objective.status.value,
        "priority": objective.priority.value,
        "criteria": objective.criteria,
        "strategies": objective.strategies,
    }
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(objective, field, value)

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="objective_updated",
        entity_type="objective",
        entity_id=objective.id,
        before=before,
        after={
            "title": objective.title,
            "status": objective.status.value,
            "priority": objective.priority.value,
            "criteria": objective.criteria,
            "strategies": objective.strategies,
        },
    )
    db.commit()
    db.refresh(objective)
    return objective


def soft_delete_objective(db: Session, user: User, objective_id: uuid.UUID) -> None:
    """Seção 13.3 — exclusão de objetivo exige confirmação (frontend) e mantém histórico."""
    patient, objective = _get_objective_or_404(db, user, objective_id)
    if not can_edit_area(db, user, patient, objective.area):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this area")

    objective.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    objective.deleted_by = user.id
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="objective_deleted",
        entity_type="objective",
        entity_id=objective.id,
    )
    db.commit()


def restore_objective(db: Session, user: User, objective_id: uuid.UUID) -> Objective:
    objective = db.get(Objective, objective_id)
    if objective is None or objective.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted objective not found")
    plan = db.get(TreatmentPlan, objective.plan_id)
    patient = patient_service.get_patient_or_404(db, user, plan.patient_id, include_deleted=True)

    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL) and not rbac_service.can_restore_deleted_data(
        db, user
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to restore objectives")

    objective.deleted_at = None
    objective.deleted_by = None
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="objective_restored",
        entity_type="objective",
        entity_id=objective.id,
    )
    db.commit()
    db.refresh(objective)
    return objective


def add_comment(
    db: Session, user: User, objective_id: uuid.UUID, body: str, mentioned_user_id: uuid.UUID | None = None
) -> ObjectiveComment:
    """Seção 13.1/32.13 — comentários por objetivo, com menção (@) opcional que
    dispara notificação direta ao profissional marcado."""
    patient, objective = _get_objective_or_404(db, user, objective_id)
    comment = ObjectiveComment(objective_id=objective.id, author_id=user.id, body=body)
    db.add(comment)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="objective_comment_added",
        entity_type="objective",
        entity_id=objective.id,
    )

    if objective.author_id != user.id:
        notification_service.create_notification(
            db,
            recipient_user_id=objective.author_id,
            actor_user_id=user.id,
            notification_type="comment",
            message=f"{user.name} comentou no objetivo \"{objective.title}\".",
            entity_type="objective",
            entity_id=objective.id,
        )

    if mentioned_user_id is not None and mentioned_user_id != user.id:
        mentioned_user = db.get(User, mentioned_user_id)
        same_tenant = mentioned_user is not None and (
            (patient.clinic_id is not None and mentioned_user.clinic_id == patient.clinic_id)
            or (patient.individual_owner_id is not None and mentioned_user.id == patient.individual_owner_id)
        )
        if same_tenant:
            notification_service.create_notification(
                db,
                recipient_user_id=mentioned_user_id,
                actor_user_id=user.id,
                notification_type="mention",
                message=f"{user.name} mencionou você em um comentário no objetivo \"{objective.title}\".",
                entity_type="objective",
                entity_id=objective.id,
            )

    db.commit()
    db.refresh(comment)
    return comment


def list_comments(db: Session, user: User, objective_id: uuid.UUID) -> list[ObjectiveComment]:
    _patient, objective = _get_objective_or_404(db, user, objective_id)
    return (
        db.query(ObjectiveComment)
        .filter(ObjectiveComment.objective_id == objective.id)
        .order_by(ObjectiveComment.created_at)
        .all()
    )


def get_history(db: Session, user: User, objective_id: uuid.UUID) -> list[AuditLog]:
    """Seção 13.1 — histórico de versões para alterações relevantes (reaproveita o AuditLog)."""
    _patient, objective = _get_objective_or_404(db, user, objective_id)
    return (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "objective", AuditLog.entity_id == objective.id)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )


def get_objective_training_ids(db: Session, objective_id: uuid.UUID) -> list[uuid.UUID]:
    return [
        row[0]
        for row in db.query(ObjectiveTraining.training_id).filter(ObjectiveTraining.objective_id == objective_id).all()
    ]


MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10MB, mesmo limite conservador da Seção 34/Resources


def list_attachments(db: Session, plan_id: uuid.UUID) -> list[TreatmentPlanAttachment]:
    return (
        db.query(TreatmentPlanAttachment)
        .filter(TreatmentPlanAttachment.plan_id == plan_id)
        .order_by(TreatmentPlanAttachment.uploaded_at.desc())
        .all()
    )


async def upload_attachment(
    db: Session, user: User, patient_id: uuid.UUID, area: TreatmentArea, file: UploadFile
) -> TreatmentPlanAttachment:
    """RF-04 — "Importar PDF" por área da grade multidisciplinar; o anexo fica
    restrito à área escolhida, sem ficar visível ou editável nas demais."""
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    if not can_edit_area(db, user, patient, area):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this area")

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted for treatment plan attachments",
        )

    body = await file.read()
    if len(body) > MAX_ATTACHMENT_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds size limit")

    plan = get_or_create_plan(db, patient)
    key = f"treatment-plan-attachments/{plan.id}/{area.value}/{uuid.uuid4()}-{file.filename}"
    file_service.upload_object(key, body, file.content_type)

    attachment = TreatmentPlanAttachment(
        plan_id=plan.id,
        area=area,
        file_key=key,
        original_filename=file.filename or "documento.pdf",
        uploaded_by_user_id=user.id,
    )
    db.add(attachment)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="treatment_plan_attachment_uploaded",
        entity_type="treatment_plan_attachment",
        entity_id=attachment.id,
        after={"area": area.value, "filename": attachment.original_filename},
    )
    db.commit()
    db.refresh(attachment)
    return attachment


def get_attachment_or_404(db: Session, user: User, attachment_id: uuid.UUID) -> tuple[Patient, TreatmentPlanAttachment]:
    attachment = db.get(TreatmentPlanAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    plan = db.get(TreatmentPlan, attachment.plan_id)
    patient = patient_service.get_patient_or_404(db, user, plan.patient_id)
    return patient, attachment


def get_attachment_view_url(attachment: TreatmentPlanAttachment) -> str:
    """Seção 15/17.2 — mesmo visualizador seguro (URL assinada e temporária) já usado
    para Recursos Terapêuticos."""
    return file_service.generate_presigned_url(attachment.file_key)


def _extract_pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception:
        # PDF corrompido ou em formato não suportado pelo parser — tratado como
        # "sem texto extraível", mesmo caminho de um PDF escaneado sem OCR.
        return ""


_CRITERIA_KEYWORDS = ("critério", "criterio", "domínio", "dominio", "%")
_STRATEGY_KEYWORDS = ("estratégia", "estrategia", "intervenç", "interven", "prompt", "ajuda")


def _draft_objective_fields_from_text(text: str) -> dict:
    """RF-05 — "Ponto técnico de atenção" do addendum recomenda começar simples:
    ler o texto extraído do PDF e mapear por palavras-chave para os 4 campos do
    objetivo, sem chamar nenhuma API de IA externa (mesmo princípio de rascunho
    determinístico já usado em report_summary_service._draft_text)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return {
            "title": "Objetivo a partir de documento anexado",
            "description": "",
            "criteria": "",
            "strategies": "",
            "extraction_note": (
                "Não foi possível extrair texto deste PDF (pode ser um documento escaneado "
                "sem OCR). Preencha os campos manualmente antes de salvar."
            ),
        }

    criteria_lines = [line for line in lines if any(k in line.lower() for k in _CRITERIA_KEYWORDS)]
    strategy_lines = [line for line in lines if any(k in line.lower() for k in _STRATEGY_KEYWORDS)]
    remaining_lines = [line for line in lines[1:] if line not in criteria_lines and line not in strategy_lines]

    return {
        "title": lines[0][:255],
        "description": " ".join(remaining_lines)[:2000]
        or "Descrição não identificada automaticamente — revise a partir do documento anexado.",
        "criteria": " ".join(criteria_lines)[:1000]
        or "Critério de domínio não identificado automaticamente — defina com base no documento anexado.",
        "strategies": " ".join(strategy_lines)[:1000]
        or "Estratégias não identificadas automaticamente — defina com base no documento anexado.",
        "extraction_note": None,
    }


def generate_objective_draft_from_attachment(
    db: Session, user: User, patient_id: uuid.UUID, attachment_id: uuid.UUID
) -> ObjectiveAIFillResponse:
    """RF-05 — "Preencher com IA": rascunho não persistido, só existe na resposta desta
    rota até o profissional revisar e salvar explicitamente o Novo Objetivo."""
    patient, attachment = get_attachment_or_404(db, user, attachment_id)
    if patient.id != patient_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    if not can_edit_area(db, user, patient, attachment.area):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this area")

    pdf_bytes = file_service.download_object(attachment.file_key)
    fields = _draft_objective_fields_from_text(_extract_pdf_text(pdf_bytes))
    return ObjectiveAIFillResponse(source_document_id=attachment.id, **fields)
