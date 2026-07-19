import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.clinical_alert import ClinicalAlert
from app.models.enums import AppointmentStatus, ClinicalAlertType, ObjectiveStatus, UserStatus, UserType
from app.models.patient import PatientAssignment
from app.models.session import ClinicalSession
from app.models.treatment_plan import Objective, TreatmentPlan
from app.models.user import User
from app.services import rbac_service

LOW_ADHERENCE_THRESHOLD_PCT = 70
ACTIVE_OBJECTIVE_STATUSES = (ObjectiveStatus.NOT_STARTED, ObjectiveStatus.IN_PROGRESS)


def _require_team_view(user: User) -> None:
    if user.clinic_id is None or user.user_type not in (UserType.CLINIC_ADMIN, UserType.SUPERVISOR):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def _therapist_row(db: Session, therapist: User, registration_cutoff: datetime.datetime) -> dict:
    assigned_patient_ids = [
        row[0]
        for row in db.query(PatientAssignment.patient_id)
        .filter(PatientAssignment.professional_id == therapist.id)
        .distinct()
        .all()
    ]

    completed_count = (
        db.query(Appointment)
        .filter(
            Appointment.professional_id == therapist.id,
            Appointment.deleted_at.is_(None),
            Appointment.status == AppointmentStatus.COMPLETED,
        )
        .count()
    )
    no_show_count = (
        db.query(Appointment)
        .filter(
            Appointment.professional_id == therapist.id,
            Appointment.deleted_at.is_(None),
            Appointment.status == AppointmentStatus.NO_SHOW,
        )
        .count()
    )
    total_concluded = completed_count + no_show_count
    session_completion_pct = round(completed_count / total_concluded * 100, 1) if total_concluded else None

    active_objective_ids: list = []
    if assigned_patient_ids:
        active_objective_ids = [
            row[0]
            for row in db.query(Objective.id)
            .join(TreatmentPlan, Objective.plan_id == TreatmentPlan.id)
            .filter(
                TreatmentPlan.patient_id.in_(assigned_patient_ids),
                Objective.deleted_at.is_(None),
                Objective.status.in_(ACTIVE_OBJECTIVE_STATUSES),
            )
            .all()
        ]
    active_objectives_count = len(active_objective_ids)

    objectives_with_no_collection_alert = 0
    if active_objective_ids:
        objectives_with_no_collection_alert = (
            db.query(ClinicalAlert)
            .filter(
                ClinicalAlert.objective_id.in_(active_objective_ids),
                ClinicalAlert.alert_type == ClinicalAlertType.NO_COLLECTION,
                ClinicalAlert.resolved_at.is_(None),
            )
            .count()
        )

    adherence_pct = (
        round((active_objectives_count - objectives_with_no_collection_alert) / active_objectives_count * 100, 1)
        if active_objectives_count
        else None
    )

    has_recent_session = False
    if assigned_patient_ids:
        has_recent_session = (
            db.query(ClinicalSession)
            .filter(
                ClinicalSession.professional_id == therapist.id,
                ClinicalSession.deleted_at.is_(None),
                ClinicalSession.occurred_at >= registration_cutoff,
            )
            .first()
            is not None
        )

    return {
        "professional_id": therapist.id,
        "professional_name": therapist.name,
        "assigned_patients_count": len(assigned_patient_ids),
        "completed_sessions_count": completed_count,
        "no_show_count": no_show_count,
        "session_completion_pct": session_completion_pct,
        "active_objectives_count": active_objectives_count,
        "treatment_plan_adherence_pct": adherence_pct,
        "low_adherence_alert": adherence_pct is not None and adherence_pct < LOW_ADHERENCE_THRESHOLD_PCT,
        "no_recent_registration_alert": bool(assigned_patient_ids) and not has_recent_session,
    }


def get_supervisor_dashboard(db: Session, user: User) -> dict:
    """Seção 29.4 — painel consolidado por equipe: percentual de sessões completas por
    terapeuta, adesão ao plano de tratamento e alertas automáticos de baixa adesão ou
    ausência de registro, restrito a administradores de clínica e supervisores."""
    _require_team_view(user)

    therapists = (
        db.query(User)
        .filter(
            User.clinic_id == user.clinic_id,
            User.user_type.in_((UserType.PROFESSIONAL, UserType.SUPERVISOR)),
            User.status == UserStatus.ACTIVE,
        )
        .order_by(User.name)
        .all()
    )

    no_collection_days = rbac_service.get_or_create_settings(db, user.clinic_id).no_collection_days
    registration_cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=no_collection_days)

    return {"therapists": [_therapist_row(db, therapist, registration_cutoff) for therapist in therapists]}
