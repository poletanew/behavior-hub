import datetime
import uuid

from fastapi import HTTPException, status
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
from app.models.treatment_plan import Objective, ObjectiveComment, ObjectiveTraining, TreatmentPlan
from app.models.user import User
from app.schemas.treatment_plan import ObjectiveCreateRequest, ObjectiveUpdateRequest
from app.services import audit_service, patient_service

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
    """Seção 13.3 — cada profissional edita objetivos da própria área ou aqueles
    para os quais recebeu permissão (aqui: vínculo FULL_ACCESS)."""
    if user.user_type in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        return True
    if user.user_type == UserType.SUPERVISOR:
        return False  # Seção 13.3 — supervisor revisa e comenta; edição fica desabilitada por padrão.

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

    objective = Objective(
        plan_id=plan.id,
        area=payload.area,
        title=payload.title,
        description=payload.description,
        criteria=payload.criteria,
        strategies=payload.strategies,
        priority=payload.priority,
        author_id=user.id,
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

    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
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


def add_comment(db: Session, user: User, objective_id: uuid.UUID, body: str) -> ObjectiveComment:
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
