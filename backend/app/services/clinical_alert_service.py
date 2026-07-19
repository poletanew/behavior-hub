import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.clinic import Clinic
from app.models.clinical_alert import ClinicalAlert
from app.models.enums import ClinicalAlertType, ObjectiveStatus, SubscriptionPlan, UserType
from app.models.patient import Patient, PatientAssignment
from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.treatment_plan import Objective, ObjectiveTraining, TreatmentPlan
from app.models.user import User
from app.schemas.clinical_alert import ClinicalAlertThresholdsUpdateRequest
from app.services import audit_service, notification_service, rbac_service
from app.services.calculations import accuracy_pct, independence_pct

DEFAULT_THRESHOLDS = {
    "no_collection_days": 14,
    "regression_window_sessions": 3,
    "regression_drop_pp": 20,
    "stagnation_session_count": 5,
    "stagnation_band_pp": 5,
    "fading_session_count": 3,
    "fading_independence_pct": 80,
    "mastery_suggestion_session_count": 3,
    "mastery_suggestion_accuracy_pct": 80,
}

THRESHOLD_FIELDS = tuple(DEFAULT_THRESHOLDS.keys())


def get_thresholds(db: Session, patient: Patient) -> dict:
    """Seção 29.1 — limiares padrão de fábrica, configuráveis por clínica no
    plano Enterprise. Contas individuais sempre usam o padrão de fábrica."""
    if patient.clinic_id is None:
        return dict(DEFAULT_THRESHOLDS)
    settings = rbac_service.get_or_create_settings(db, patient.clinic_id)
    return {field: getattr(settings, field) for field in THRESHOLD_FIELDS}


def update_thresholds(db: Session, user: User, payload: ClinicalAlertThresholdsUpdateRequest):
    if user.user_type != UserType.CLINIC_ADMIN or user.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clinic admins can configure alert thresholds")

    clinic = db.get(Clinic, user.clinic_id)
    if clinic is None or clinic.subscription_plan != SubscriptionPlan.ENTERPRISE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Alert thresholds are configurable only on the Enterprise plan",
        )

    settings = rbac_service.get_or_create_settings(db, user.clinic_id)
    before = {field: getattr(settings, field) for field in THRESHOLD_FIELDS}
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if value is not None:
            setattr(settings, field, value)

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="clinical_alert_thresholds_updated",
        entity_type="clinic_permission_settings",
        entity_id=settings.id,
        before=before,
        after=updates,
    )
    db.commit()
    db.refresh(settings)
    return settings


def _objective_session_series(db: Session, objective: Objective, patient_id: uuid.UUID) -> list[dict]:
    """Seção 29.1 — série histórica de tentativas por sessão para os treinos
    vinculados ao objetivo (ObjectiveTraining), em ordem cronológica.
    Objetivos sem nenhum treino vinculado nunca geram alertas — não há como
    derivar uma série de tentativas sem esse vínculo estrutural."""
    training_ids = [
        row[0] for row in db.query(ObjectiveTraining.training_id).filter(ObjectiveTraining.objective_id == objective.id).all()
    ]
    if not training_ids:
        return []

    rows = (
        db.query(ClinicalSession.id, ClinicalSession.occurred_at, Trial)
        .join(SessionTraining, SessionTraining.session_id == ClinicalSession.id)
        .join(Trial, Trial.session_training_id == SessionTraining.id)
        .filter(
            SessionTraining.training_id.in_(training_ids),
            ClinicalSession.patient_id == patient_id,
            ClinicalSession.deleted_at.is_(None),
            Trial.deleted_at.is_(None),
        )
        .all()
    )

    sessions: dict[uuid.UUID, dict] = {}
    for session_id, occurred_at, trial in rows:
        bucket = sessions.setdefault(session_id, {"occurred_at": occurred_at, "trials": []})
        bucket["trials"].append(trial)

    series = [
        {
            "occurred_at": bucket["occurred_at"],
            "accuracy_pct": accuracy_pct(bucket["trials"]),
            "independence_pct": independence_pct(bucket["trials"]),
        }
        for bucket in sessions.values()
    ]
    series.sort(key=lambda s: s["occurred_at"])
    return series


def _evaluate_no_collection(series: list[dict], thresholds: dict, now: datetime.datetime) -> dict | None:
    """Seção 29.1 — "nenhuma tentativa registrada... há mais de 14 dias corridos".
    Sem nenhuma tentativa histórica, não há uma data de referência para contar
    dias — objetivos nunca coletados não disparam este alerta especificamente
    (eles não têm série alguma para os outros três alertas também)."""
    if not series:
        return None
    last_at = series[-1]["occurred_at"]
    days_since = (now - last_at).days
    if days_since > thresholds["no_collection_days"]:
        return {"days_since_last_trial": days_since, "last_trial_at": last_at.isoformat()}
    return None


def _evaluate_regression(series: list[dict], thresholds: dict) -> dict | None:
    """Seção 29.1 — média móvel das últimas N sessões cai X pontos percentuais
    ou mais em relação à média móvel das N sessões anteriores (AC-16)."""
    window = thresholds["regression_window_sessions"]
    if len(series) < window * 2:
        return None

    recent_vals = [s["accuracy_pct"] for s in series[-window:] if s["accuracy_pct"] is not None]
    previous_vals = [s["accuracy_pct"] for s in series[-window * 2 : -window] if s["accuracy_pct"] is not None]
    if len(recent_vals) < window or len(previous_vals) < window:
        return None

    recent_avg = sum(recent_vals) / len(recent_vals)
    previous_avg = sum(previous_vals) / len(previous_vals)
    drop = previous_avg - recent_avg
    if drop >= thresholds["regression_drop_pp"]:
        return {
            "recent_avg_pct": round(recent_avg, 1),
            "previous_avg_pct": round(previous_avg, 1),
            "drop_pp": round(drop, 1),
        }
    return None


def _evaluate_stagnation(series: list[dict], thresholds: dict, objective_status: ObjectiveStatus) -> dict | None:
    """Seção 29.1 — percentual de acerto permanece dentro de uma faixa de ±N
    pontos percentuais por M sessões consecutivas, sem atingir o critério de
    domínio. Interpretação adotada para "faixa de ±N pontos": a variação
    (máximo - mínimo) entre as M sessões não ultrapassa N pontos percentuais —
    decisão de engenharia documentada aqui, já que o PRD não formaliza a
    fórmula exata como fez para regressão."""
    if objective_status == ObjectiveStatus.MASTERED:
        return None

    count = thresholds["stagnation_session_count"]
    if len(series) < count:
        return None

    vals = [s["accuracy_pct"] for s in series[-count:] if s["accuracy_pct"] is not None]
    if len(vals) < count:
        return None

    spread = max(vals) - min(vals)
    if spread <= thresholds["stagnation_band_pp"]:
        return {"accuracy_values_pct": vals, "range_pp": round(spread, 1)}
    return None


def _evaluate_fading_candidate(series: list[dict], thresholds: dict) -> dict | None:
    """Seção 29.1 — percentual de independência >= N% em M sessões consecutivas."""
    count = thresholds["fading_session_count"]
    if len(series) < count:
        return None

    vals = [s["independence_pct"] for s in series[-count:] if s["independence_pct"] is not None]
    if len(vals) < count:
        return None

    if all(v >= thresholds["fading_independence_pct"] for v in vals):
        return {"independence_values_pct": vals}
    return None


def _message_for(alert_type: ClinicalAlertType, detail: dict, thresholds: dict) -> str:
    """Seção 29.9 — mensagens no mesmo formato dos exemplos do PRD."""
    if alert_type == ClinicalAlertType.NO_COLLECTION:
        return f"Este programa está sem coleta há {detail['days_since_last_trial']} dias."
    if alert_type == ClinicalAlertType.REGRESSION:
        return f"Paciente apresentou queda de {detail['drop_pp']}% no percentual de acerto."
    if alert_type == ClinicalAlertType.STAGNATION:
        return (
            f"Objetivo sem progresso perceptível nas últimas {thresholds['stagnation_session_count']} "
            f"sessões (variação de {detail['range_pp']} pontos percentuais)."
        )
    return (
        f"Objetivo pode ser considerado candidato a fading (redução de ajuda) — independência "
        f"≥{thresholds['fading_independence_pct']}% nas últimas {thresholds['fading_session_count']} sessões."
    )


def _upsert_alert(
    db: Session,
    patient: Patient,
    objective: Objective,
    alert_type: ClinicalAlertType,
    detail: dict,
    thresholds: dict,
    now: datetime.datetime,
) -> ClinicalAlert | None:
    """Retorna o ClinicalAlert recém-criado, ou None se já havia um ativo do
    mesmo tipo para este objetivo (apenas atualiza o detalhe com os números
    mais recentes, sem notificar de novo)."""
    active = (
        db.query(ClinicalAlert)
        .filter(
            ClinicalAlert.objective_id == objective.id,
            ClinicalAlert.alert_type == alert_type,
            ClinicalAlert.resolved_at.is_(None),
        )
        .first()
    )
    if active is not None:
        active.detail = detail
        return None

    alert = ClinicalAlert(
        clinic_id=patient.clinic_id,
        individual_owner_id=patient.individual_owner_id,
        patient_id=patient.id,
        objective_id=objective.id,
        alert_type=alert_type,
        message=_message_for(alert_type, detail, thresholds),
        detail=detail,
        triggered_at=now,
    )
    db.add(alert)
    return alert


def _resolve_if_active(db: Session, objective_id: uuid.UUID, alert_type: ClinicalAlertType, now: datetime.datetime) -> None:
    active = (
        db.query(ClinicalAlert)
        .filter(
            ClinicalAlert.objective_id == objective_id,
            ClinicalAlert.alert_type == alert_type,
            ClinicalAlert.resolved_at.is_(None),
        )
        .first()
    )
    if active is not None:
        active.resolved_at = now


def _notify_new_alert(db: Session, patient: Patient, alert: ClinicalAlert) -> None:
    """Seção 19.2 — ClinicalAlertTriggered: notifica supervisor/profissional
    vinculado. Contas individuais não recebem notificação de si mesmas."""
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
            notification_type="clinical_alert",
            message=f"{patient.name}: {alert.message}",
            entity_type="clinical_alert",
            entity_id=alert.id,
        )


def recompute_alerts_for_objective(db: Session, objective: Objective) -> list[ClinicalAlert]:
    """Seção 29.1/29.9 — recalcula as 4 regras para um objetivo e retorna
    apenas os alertas recém-disparados nesta chamada (para notificação)."""
    now = datetime.datetime.now(datetime.timezone.utc)

    if objective.deleted_at is not None:
        return []

    plan = db.get(TreatmentPlan, objective.plan_id)
    patient = db.get(Patient, plan.patient_id) if plan else None
    if patient is None or patient.deleted_at is not None:
        return []

    if objective.status == ObjectiveStatus.DISCONTINUED:
        for alert_type in ClinicalAlertType:
            _resolve_if_active(db, objective.id, alert_type, now)
        db.commit()
        return []

    thresholds = get_thresholds(db, patient)
    series = _objective_session_series(db, objective, patient.id)

    checks = (
        (ClinicalAlertType.NO_COLLECTION, _evaluate_no_collection(series, thresholds, now)),
        (ClinicalAlertType.REGRESSION, _evaluate_regression(series, thresholds)),
        (ClinicalAlertType.STAGNATION, _evaluate_stagnation(series, thresholds, objective.status)),
        (ClinicalAlertType.FADING_CANDIDATE, _evaluate_fading_candidate(series, thresholds)),
    )

    new_alerts: list[ClinicalAlert] = []
    for alert_type, detail in checks:
        if detail is not None:
            new_alert = _upsert_alert(db, patient, objective, alert_type, detail, thresholds, now)
            if new_alert is not None:
                new_alerts.append(new_alert)
        else:
            _resolve_if_active(db, objective.id, alert_type, now)

    db.commit()
    for alert in new_alerts:
        db.refresh(alert)
        _notify_new_alert(db, patient, alert)
    if new_alerts:
        db.commit()
    return new_alerts


def recompute_alerts_for_training(db: Session, patient_id: uuid.UUID, training_id: uuid.UUID) -> list[ClinicalAlert]:
    """Seção 19.2 — TrialCreated/Updated/Deleted: recalcula os alertas dos
    objetivos vinculados a este treino para este paciente (chamado logo após
    salvar uma tentativa, para refletir regressão/fading em tempo real —
    Seção 29.1/AC-16). O alerta de "sem coleta" também é pego aqui quando uma
    nova tentativa resolve um alerta existente."""
    objective_ids = (
        db.query(ObjectiveTraining.objective_id)
        .join(Objective, Objective.id == ObjectiveTraining.objective_id)
        .join(TreatmentPlan, TreatmentPlan.id == Objective.plan_id)
        .filter(ObjectiveTraining.training_id == training_id, TreatmentPlan.patient_id == patient_id)
        .all()
    )
    all_new: list[ClinicalAlert] = []
    for (objective_id,) in objective_ids:
        objective = db.get(Objective, objective_id)
        if objective is not None:
            all_new.extend(recompute_alerts_for_objective(db, objective))
    return all_new


def recompute_alerts_for_patient(db: Session, patient: Patient) -> list[ClinicalAlert]:
    plan = db.query(TreatmentPlan).filter(TreatmentPlan.patient_id == patient.id).first()
    if plan is None:
        return []
    objectives = db.query(Objective).filter(Objective.plan_id == plan.id, Objective.deleted_at.is_(None)).all()

    all_new: list[ClinicalAlert] = []
    for objective in objectives:
        all_new.extend(recompute_alerts_for_objective(db, objective))
    return all_new


def list_active_alerts(db: Session, patient: Patient) -> list[dict]:
    alerts = (
        db.query(ClinicalAlert, Objective.title)
        .join(Objective, ClinicalAlert.objective_id == Objective.id)
        .filter(ClinicalAlert.patient_id == patient.id, ClinicalAlert.resolved_at.is_(None))
        .order_by(ClinicalAlert.triggered_at.desc())
        .all()
    )
    return [
        {
            "id": alert.id,
            "patient_id": alert.patient_id,
            "objective_id": alert.objective_id,
            "objective_title": title,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "detail": alert.detail,
            "triggered_at": alert.triggered_at,
            "resolved_at": alert.resolved_at,
        }
        for alert, title in alerts
    ]
