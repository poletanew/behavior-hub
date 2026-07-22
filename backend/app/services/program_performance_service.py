import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import ObjectiveStatus, UserType
from app.models.patient import Patient
from app.models.training import Training
from app.models.treatment_plan import Objective, ObjectiveTraining, TreatmentPlan
from app.models.user import User

# Addendum v3.0, RF-32 — "mínimo 2 pacientes": piso estatístico/de privacidade
# para não expor uma taxa de domínio derivada de um único paciente.
MIN_PATIENTS_FOR_PROGRAM_STATS = 2


def _require_manager_view(user: User) -> None:
    if user.clinic_id is None or user.user_type != UserType.CLINIC_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def get_program_performance(db: Session, user: User) -> list[dict]:
    """Addendum v3.0, RF-32 — desempenho agregado por treino da Training
    Library (taxa média de domínio, tempo médio até dominar), restrito a
    administradores da clínica (mesma visão de negócio do Painel de Gestão,
    Seção 29.5)."""
    _require_manager_view(user)

    rows = (
        db.query(Training.id, Training.title, Objective, TreatmentPlan.patient_id)
        .join(ObjectiveTraining, ObjectiveTraining.training_id == Training.id)
        .join(Objective, ObjectiveTraining.objective_id == Objective.id)
        .join(TreatmentPlan, Objective.plan_id == TreatmentPlan.id)
        .join(Patient, TreatmentPlan.patient_id == Patient.id)
        .filter(Patient.clinic_id == user.clinic_id, Objective.deleted_at.is_(None))
        .all()
    )

    by_training: dict[uuid.UUID, dict] = {}
    for training_id, training_title, objective, patient_id in rows:
        entry = by_training.setdefault(training_id, {"title": training_title, "objectives": [], "patients": set()})
        entry["objectives"].append(objective)
        entry["patients"].add(patient_id)

    mastered_objective_ids = [
        o.id
        for entry in by_training.values()
        for o in entry["objectives"]
        if o.status == ObjectiveStatus.MASTERED
    ]

    mastery_dates: dict[uuid.UUID, datetime.datetime] = {}
    if mastered_objective_ids:
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "objective",
                AuditLog.entity_id.in_(mastered_objective_ids),
                AuditLog.action == "objective_updated",
            )
            .order_by(AuditLog.timestamp)
            .all()
        )
        for log in logs:
            after_status = (log.after or {}).get("status")
            before_status = (log.before or {}).get("status")
            if after_status == "mastered" and before_status != "mastered" and log.entity_id not in mastery_dates:
                mastery_dates[log.entity_id] = log.timestamp

    results = []
    for training_id, entry in by_training.items():
        if len(entry["patients"]) < MIN_PATIENTS_FOR_PROGRAM_STATS:
            continue

        objectives = entry["objectives"]
        mastered = [o for o in objectives if o.status == ObjectiveStatus.MASTERED]
        mastery_rate_pct = round(len(mastered) / len(objectives) * 100, 1)

        days_to_mastery = []
        for objective in mastered:
            mastered_at = mastery_dates.get(objective.id)
            if mastered_at is None:
                continue
            created_at = objective.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=datetime.timezone.utc)
            days_to_mastery.append((mastered_at - created_at).days)
        average_days_to_mastery = (
            round(sum(days_to_mastery) / len(days_to_mastery), 1) if days_to_mastery else None
        )

        results.append(
            {
                "training_id": training_id,
                "training_title": entry["title"],
                "patients_count": len(entry["patients"]),
                "objectives_count": len(objectives),
                "mastery_rate_pct": mastery_rate_pct,
                "average_days_to_mastery": average_days_to_mastery,
            }
        )

    results.sort(key=lambda r: r["training_title"])
    return results
