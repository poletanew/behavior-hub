import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.clinical_suggestion import ClinicalSuggestion
from app.models.enums import ObjectiveStatus, SuggestionStatus, SuggestionType, TrainingVisibility, UserType
from app.models.patient import Patient, PatientAssignment
from app.models.training import Training, TrainingCategory
from app.models.treatment_plan import Objective, ObjectiveTraining, TreatmentPlan
from app.models.user import User
from app.services import audit_service, clinical_alert_service, notification_service, patient_service

NEW_PROGRAM_SUGGESTION_LIMIT = 3


def _resolve_patient(db: Session, objective: Objective) -> Patient | None:
    plan = db.get(TreatmentPlan, objective.plan_id)
    return db.get(Patient, plan.patient_id) if plan else None


def _evaluate_mastery_ready(series: list[dict], thresholds: dict, objective_status: ObjectiveStatus) -> dict | None:
    """Seção 29.9 — "objetivo pode ser considerado dominado com base no
    critério configurado": percentual de acerto >= limiar nas últimas N
    sessões, para um objetivo ainda não marcado como dominado."""
    if objective_status == ObjectiveStatus.MASTERED:
        return None

    count = thresholds["mastery_suggestion_session_count"]
    if len(series) < count:
        return None

    vals = [s["accuracy_pct"] for s in series[-count:] if s["accuracy_pct"] is not None]
    if len(vals) < count:
        return None

    if all(v >= thresholds["mastery_suggestion_accuracy_pct"] for v in vals):
        return {"accuracy_values_pct": vals}
    return None


def _notify_new_suggestion(db: Session, patient: Patient, suggestion: ClinicalSuggestion) -> None:
    if patient.clinic_id is None:
        return

    recipient_ids: set[uuid.UUID] = set()
    admins_and_supervisors = (
        db.query(User.id)
        .filter(User.clinic_id == patient.clinic_id, User.user_type.in_((UserType.CLINIC_ADMIN, UserType.SUPERVISOR)))
        .all()
    )
    recipient_ids.update(row[0] for row in admins_and_supervisors)
    assigned = db.query(PatientAssignment.professional_id).filter(PatientAssignment.patient_id == patient.id).all()
    recipient_ids.update(row[0] for row in assigned)

    for recipient_id in recipient_ids:
        notification_service.create_notification(
            db,
            recipient_user_id=recipient_id,
            actor_user_id=None,
            notification_type="clinical_suggestion",
            message=f"{patient.name}: {suggestion.message}",
            entity_type="clinical_suggestion",
            entity_id=suggestion.id,
        )


def _create_objective_suggestion(
    db: Session,
    patient: Patient,
    objective: Objective,
    suggestion_type: SuggestionType,
    message: str,
    detail: dict,
) -> ClinicalSuggestion | None:
    """Cria a sugestão apenas se nenhuma outra já existir (em qualquer status)
    para este objetivo/tipo — uma vez decidida pelo profissional, não é
    recriada mesmo que a condição continue verdadeira."""
    existing = (
        db.query(ClinicalSuggestion)
        .filter(ClinicalSuggestion.objective_id == objective.id, ClinicalSuggestion.suggestion_type == suggestion_type)
        .first()
    )
    if existing is not None:
        return None

    suggestion = ClinicalSuggestion(
        clinic_id=patient.clinic_id,
        individual_owner_id=patient.individual_owner_id,
        patient_id=patient.id,
        objective_id=objective.id,
        suggestion_type=suggestion_type,
        message=message,
        detail=detail,
    )
    db.add(suggestion)
    return suggestion


def recompute_suggestions_for_objective(db: Session, objective: Objective) -> list[ClinicalSuggestion]:
    """Seção 29.1 (Fase 4b) — sugestões de fading e de objetivo dominado,
    ligadas a um objetivo específico. Reaproveita a mesma série histórica e
    limiares dos Alertas Clínicos (clinical_alert_service), já que ambos
    partem exatamente da mesma coleta de tentativas."""
    if objective.deleted_at is not None or objective.status == ObjectiveStatus.DISCONTINUED:
        return []

    patient = _resolve_patient(db, objective)
    if patient is None or patient.deleted_at is not None:
        return []

    thresholds = clinical_alert_service.get_thresholds(db, patient)
    series = clinical_alert_service._objective_session_series(db, objective, patient.id)

    new_suggestions: list[ClinicalSuggestion] = []

    fading_detail = clinical_alert_service._evaluate_fading_candidate(series, thresholds)
    if fading_detail is not None:
        message = (
            "Sugestão: considerar reduzir o nível de ajuda no próximo atendimento — independência "
            f"≥{thresholds['fading_independence_pct']}% nas últimas {thresholds['fading_session_count']} sessões."
        )
        created = _create_objective_suggestion(db, patient, objective, SuggestionType.FADING, message, fading_detail)
        if created is not None:
            new_suggestions.append(created)

    mastery_detail = _evaluate_mastery_ready(series, thresholds, objective.status)
    if mastery_detail is not None:
        message = "Objetivo pode ser considerado dominado com base no critério configurado."
        created = _create_objective_suggestion(
            db, patient, objective, SuggestionType.MASTERY_READY, message, mastery_detail
        )
        if created is not None:
            new_suggestions.append(created)

    if new_suggestions:
        db.commit()
        for suggestion in new_suggestions:
            db.refresh(suggestion)
            _notify_new_suggestion(db, patient, suggestion)
        db.commit()
    return new_suggestions


def _visible_training_scope(patient: Patient):
    scope = [Training.visibility == TrainingVisibility.SYSTEM]
    if patient.clinic_id is not None:
        scope.append((Training.visibility == TrainingVisibility.CLINIC_SHARED) & (Training.clinic_id == patient.clinic_id))
    return or_(*scope)


def recompute_new_program_suggestions(db: Session, patient: Patient) -> list[ClinicalSuggestion]:
    """Seção 29.1/29.7 — "sugerir novos programas com base em lacunas
    identificadas na área trabalhada": compara as categorias de treino já
    trabalhadas ativamente por este paciente contra a Training Library visível
    a ele, e sugere um treino de uma categoria ainda não trabalhada. Só faz
    sentido comparar quando o paciente já tem pelo menos uma área em
    andamento — sem isso não há "área trabalhada" de referência."""
    plan = db.query(TreatmentPlan).filter(TreatmentPlan.patient_id == patient.id).first()
    if plan is None:
        return []

    worked_category_ids = {
        row[0]
        for row in db.query(Training.category_id)
        .join(ObjectiveTraining, ObjectiveTraining.training_id == Training.id)
        .join(Objective, Objective.id == ObjectiveTraining.objective_id)
        .filter(
            Objective.plan_id == plan.id,
            Objective.deleted_at.is_(None),
            Objective.status.in_((ObjectiveStatus.NOT_STARTED, ObjectiveStatus.IN_PROGRESS)),
        )
        .all()
    }
    if not worked_category_ids:
        return []

    candidates = (
        db.query(Training, TrainingCategory)
        .join(TrainingCategory, Training.category_id == TrainingCategory.id)
        .filter(_visible_training_scope(patient), ~Training.category_id.in_(worked_category_ids))
        .order_by(TrainingCategory.name, Training.title)
        .all()
    )

    seen_categories: set[uuid.UUID] = set()
    new_suggestions: list[ClinicalSuggestion] = []
    for training, category in candidates:
        if category.id in seen_categories:
            continue
        seen_categories.add(category.id)
        if len(seen_categories) > NEW_PROGRAM_SUGGESTION_LIMIT:
            break

        existing = (
            db.query(ClinicalSuggestion)
            .filter(
                ClinicalSuggestion.patient_id == patient.id,
                ClinicalSuggestion.training_id == training.id,
                ClinicalSuggestion.suggestion_type == SuggestionType.NEW_PROGRAM,
            )
            .first()
        )
        if existing is not None:
            continue

        suggestion = ClinicalSuggestion(
            clinic_id=patient.clinic_id,
            individual_owner_id=patient.individual_owner_id,
            patient_id=patient.id,
            training_id=training.id,
            suggestion_type=SuggestionType.NEW_PROGRAM,
            message=f'Sugestão: iniciar o treino "{training.title}" ({category.name}) — área ainda não trabalhada no plano deste paciente.',
            detail={"category_name": category.name, "training_title": training.title},
        )
        db.add(suggestion)
        new_suggestions.append(suggestion)

    if new_suggestions:
        db.commit()
        for suggestion in new_suggestions:
            db.refresh(suggestion)
            _notify_new_suggestion(db, patient, suggestion)
        db.commit()
    return new_suggestions


def recompute_suggestions_for_training(db: Session, patient_id: uuid.UUID, training_id: uuid.UUID) -> list[ClinicalSuggestion]:
    """Seção 19.2 — chamado logo após salvar uma tentativa, mesma ocasião do
    recálculo dos Alertas Clínicos."""
    objective_ids = (
        db.query(ObjectiveTraining.objective_id)
        .join(Objective, Objective.id == ObjectiveTraining.objective_id)
        .join(TreatmentPlan, TreatmentPlan.id == Objective.plan_id)
        .filter(ObjectiveTraining.training_id == training_id, TreatmentPlan.patient_id == patient_id)
        .all()
    )
    all_new: list[ClinicalSuggestion] = []
    for (objective_id,) in objective_ids:
        objective = db.get(Objective, objective_id)
        if objective is not None:
            all_new.extend(recompute_suggestions_for_objective(db, objective))

    patient = db.get(Patient, patient_id)
    if patient is not None:
        all_new.extend(recompute_new_program_suggestions(db, patient))
    return all_new


def recompute_suggestions_for_patient(db: Session, patient: Patient) -> list[ClinicalSuggestion]:
    plan = db.query(TreatmentPlan).filter(TreatmentPlan.patient_id == patient.id).first()
    all_new: list[ClinicalSuggestion] = []
    if plan is not None:
        objectives = db.query(Objective).filter(Objective.plan_id == plan.id, Objective.deleted_at.is_(None)).all()
        for objective in objectives:
            all_new.extend(recompute_suggestions_for_objective(db, objective))
    all_new.extend(recompute_new_program_suggestions(db, patient))
    return all_new


def list_suggestions(db: Session, patient: Patient) -> list[dict]:
    rows = (
        db.query(ClinicalSuggestion, Objective.title, Training.title)
        .outerjoin(Objective, ClinicalSuggestion.objective_id == Objective.id)
        .outerjoin(Training, ClinicalSuggestion.training_id == Training.id)
        .filter(ClinicalSuggestion.patient_id == patient.id)
        .order_by(ClinicalSuggestion.created_at.desc())
        .all()
    )
    return [
        {
            "id": suggestion.id,
            "patient_id": suggestion.patient_id,
            "objective_id": suggestion.objective_id,
            "objective_title": objective_title,
            "training_id": suggestion.training_id,
            "training_title": training_title,
            "suggestion_type": suggestion.suggestion_type,
            "message": suggestion.message,
            "detail": suggestion.detail,
            "status": suggestion.status,
            "created_at": suggestion.created_at,
            "decided_at": suggestion.decided_at,
        }
        for suggestion, objective_title, training_title in rows
    ]


def _get_suggestion_or_404(db: Session, user: User, suggestion_id: uuid.UUID) -> tuple[Patient, ClinicalSuggestion]:
    suggestion = db.get(ClinicalSuggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
    patient = patient_service.get_patient_or_404(db, user, suggestion.patient_id)
    return patient, suggestion


def _to_dict(db: Session, suggestion: ClinicalSuggestion) -> dict:
    objective_title = db.get(Objective, suggestion.objective_id).title if suggestion.objective_id else None
    training_title = db.get(Training, suggestion.training_id).title if suggestion.training_id else None
    return {
        "id": suggestion.id,
        "patient_id": suggestion.patient_id,
        "objective_id": suggestion.objective_id,
        "objective_title": objective_title,
        "training_id": suggestion.training_id,
        "training_title": training_title,
        "suggestion_type": suggestion.suggestion_type,
        "message": suggestion.message,
        "detail": suggestion.detail,
        "status": suggestion.status,
        "created_at": suggestion.created_at,
        "decided_at": suggestion.decided_at,
    }


def _decide_suggestion(db: Session, user: User, suggestion_id: uuid.UUID, new_status: SuggestionStatus) -> dict:
    _patient, suggestion = _get_suggestion_or_404(db, user, suggestion_id)
    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suggestion already decided")

    suggestion.status = new_status
    suggestion.decided_at = datetime.datetime.now(datetime.timezone.utc)
    suggestion.decided_by_user_id = user.id

    audit_service.record(
        db,
        actor_user_id=user.id,
        action=f"clinical_suggestion_{new_status.value}",
        entity_type="clinical_suggestion",
        entity_id=suggestion.id,
        after={"status": new_status.value},
    )
    db.commit()
    db.refresh(suggestion)
    return _to_dict(db, suggestion)


def approve_suggestion(db: Session, user: User, suggestion_id: uuid.UUID) -> dict:
    """Aprovar registra a decisão do profissional (Seção 29.1: "toda sugestão
    é uma recomendação editável... o profissional aprova, ajusta ou
    descarta") — não aplica nenhuma mudança automática nos dados clínicos;
    a ação real (marcar como dominado, criar o objetivo, reduzir o nível de
    ajuda) continua sendo feita pelo profissional nos fluxos já existentes."""
    return _decide_suggestion(db, user, suggestion_id, SuggestionStatus.APPROVED)


def dismiss_suggestion(db: Session, user: User, suggestion_id: uuid.UUID) -> dict:
    return _decide_suggestion(db, user, suggestion_id, SuggestionStatus.DISMISSED)
