import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, PatientStatus, UserStatus, UserType
from app.models.patient import Patient
from app.models.session import ClinicalSession
from app.models.user import User

CONCLUDED_APPOINTMENT_STATUSES = (
    AppointmentStatus.COMPLETED,
    AppointmentStatus.NO_SHOW,
    AppointmentStatus.CANCELLED,
)


def _require_manager_view(user: User) -> None:
    if user.clinic_id is None or user.user_type != UserType.CLINIC_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def get_manager_dashboard(
    db: Session,
    user: User,
    *,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> dict:
    """Seção 29.5 — visão de negócio da clínica (pacientes/profissionais ativos, sessões
    realizadas, horas clínicas, ocupação), derivada dos mesmos dados operacionais já
    coletados pelo resto do sistema, sem planilhas paralelas. Restrita ao administrador
    da clínica (contas individuais e outros papéis não têm essa visão de negócio)."""
    _require_manager_view(user)

    today = datetime.date.today()
    if date_from is None:
        date_from = today.replace(day=1)
    if date_to is None:
        date_to = today

    period_start = datetime.datetime.combine(date_from, datetime.time.min, tzinfo=datetime.timezone.utc)
    period_end = datetime.datetime.combine(date_to, datetime.time.max, tzinfo=datetime.timezone.utc)

    active_patients_count = (
        db.query(Patient)
        .filter(
            Patient.clinic_id == user.clinic_id,
            Patient.deleted_at.is_(None),
            Patient.status == PatientStatus.ACTIVE,
        )
        .count()
    )
    active_professionals_count = (
        db.query(User)
        .filter(
            User.clinic_id == user.clinic_id,
            User.status == UserStatus.ACTIVE,
            User.user_type.in_((UserType.PROFESSIONAL, UserType.SUPERVISOR)),
        )
        .count()
    )

    sessions_count = (
        db.query(ClinicalSession)
        .filter(
            ClinicalSession.clinic_id == user.clinic_id,
            ClinicalSession.deleted_at.is_(None),
            ClinicalSession.occurred_at >= period_start,
            ClinicalSession.occurred_at <= period_end,
        )
        .count()
    )

    completed_appointments = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == user.clinic_id,
            Appointment.deleted_at.is_(None),
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.scheduled_start >= period_start,
            Appointment.scheduled_start <= period_end,
        )
        .all()
    )
    clinical_hours = round(
        sum((a.scheduled_end - a.scheduled_start).total_seconds() for a in completed_appointments) / 3600, 1
    )

    concluded_count = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == user.clinic_id,
            Appointment.deleted_at.is_(None),
            Appointment.status.in_(CONCLUDED_APPOINTMENT_STATUSES),
            Appointment.scheduled_start >= period_start,
            Appointment.scheduled_start <= period_end,
        )
        .count()
    )
    occupancy_rate_pct = round(len(completed_appointments) / concluded_count * 100, 1) if concluded_count else None

    return {
        "period_start": date_from,
        "period_end": date_to,
        "active_patients_count": active_patients_count,
        "active_professionals_count": active_professionals_count,
        "sessions_count": sessions_count,
        "clinical_hours": clinical_hours,
        "occupancy_rate_pct": occupancy_rate_pct,
    }
