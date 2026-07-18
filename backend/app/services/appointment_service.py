import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, CancellationReason, UserType
from app.models.patient import Patient, PatientAssignment
from app.models.user import User
from app.schemas.appointment import AppointmentCreateRequest, AppointmentUpdateRequest
from app.services import audit_service, notification_service, patient_service

CONSECUTIVE_NO_SHOW_THRESHOLD = 2
ACTIVE_STATUSES = (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED)


def _tenant_scope_filter(user: User):
    if user.clinic_id is not None:
        return Appointment.clinic_id == user.clinic_id
    return Appointment.individual_owner_id == user.id


def _visibility_filter(user: User):
    """Seção 17.1 — profissional/supervisor vê a própria agenda e a de pacientes atribuídos;
    admin de clínica e conta individual veem todo o tenant."""
    if user.user_type == UserType.CLINIC_ADMIN or user.clinic_id is None:
        return None
    assigned_patient_ids = select(PatientAssignment.patient_id).where(
        PatientAssignment.professional_id == user.id
    )
    return or_(Appointment.professional_id == user.id, Appointment.patient_id.in_(assigned_patient_ids))


def _has_conflict(
    db: Session, professional_id: uuid.UUID, start: datetime.datetime, end: datetime.datetime, exclude_id=None
) -> bool:
    """Seção 32.2 — bloqueio de conflito de horário para o mesmo profissional.
    Compromissos cancelados/faltas liberam o horário; os demais status bloqueiam."""
    query = db.query(Appointment).filter(
        Appointment.professional_id == professional_id,
        Appointment.deleted_at.is_(None),
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.scheduled_start < end,
        Appointment.scheduled_end > start,
    )
    if exclude_id is not None:
        query = query.filter(Appointment.id != exclude_id)
    return db.query(query.exists()).scalar()


def _validate_professional(db: Session, user: User, professional_id: uuid.UUID) -> User:
    professional = db.get(User, professional_id)
    if professional is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found")
    if user.clinic_id is not None:
        if professional.clinic_id != user.clinic_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found in this clinic")
    elif professional.id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found")
    return professional


def _to_response_dict(appointment: Appointment, patient_name: str, professional_name: str) -> dict:
    return {
        "id": appointment.id,
        "patient_id": appointment.patient_id,
        "patient_name": patient_name,
        "professional_id": appointment.professional_id,
        "professional_name": professional_name,
        "scheduled_start": appointment.scheduled_start,
        "scheduled_end": appointment.scheduled_end,
        "status": appointment.status,
        "cancellation_reason": appointment.cancellation_reason,
        "status_notes": appointment.status_notes,
        "notes": appointment.notes,
        "session_id": appointment.session_id,
        "deleted_at": appointment.deleted_at,
        "created_at": appointment.created_at,
    }


def _enrich(db: Session, appointments: list[Appointment]) -> list[dict]:
    if not appointments:
        return []
    patient_names = {
        p.id: p.name
        for p in db.query(Patient).filter(Patient.id.in_({a.patient_id for a in appointments})).all()
    }
    professional_names = {
        u.id: u.name
        for u in db.query(User).filter(User.id.in_({a.professional_id for a in appointments})).all()
    }
    return [
        _to_response_dict(a, patient_names.get(a.patient_id, "?"), professional_names.get(a.professional_id, "?"))
        for a in appointments
    ]


def create_appointment(db: Session, user: User, payload: AppointmentCreateRequest) -> dict:
    patient = patient_service.get_patient_or_404(db, user, payload.patient_id)
    professional = _validate_professional(db, user, payload.professional_id)

    if _has_conflict(db, professional.id, payload.scheduled_start, payload.scheduled_end):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This professional already has an appointment in this time range",
        )

    appointment = Appointment(
        patient_id=patient.id,
        professional_id=professional.id,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        notes=payload.notes,
        status=AppointmentStatus.SCHEDULED,
        created_by_user_id=user.id,
    )
    if user.clinic_id is not None:
        appointment.clinic_id = user.clinic_id
    else:
        appointment.individual_owner_id = user.id

    db.add(appointment)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="appointment_scheduled",
        entity_type="appointment",
        entity_id=appointment.id,
        after={"patient_id": str(patient.id), "scheduled_start": payload.scheduled_start.isoformat()},
    )
    db.commit()
    db.refresh(appointment)
    return _to_response_dict(appointment, patient.name, professional.name)


def get_enriched_appointment(db: Session, user: User, appointment_id: uuid.UUID) -> dict:
    appointment = get_appointment_or_404(db, user, appointment_id)
    return _enrich(db, [appointment])[0]


def get_appointment_or_404(db: Session, user: User, appointment_id: uuid.UUID, *, include_deleted: bool = False) -> Appointment:
    query = db.query(Appointment).filter(Appointment.id == appointment_id, _tenant_scope_filter(user))
    if not include_deleted:
        query = query.filter(Appointment.deleted_at.is_(None))
    visibility = _visibility_filter(user)
    if visibility is not None:
        query = query.filter(visibility)
    appointment = query.first()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


def list_appointments(
    db: Session,
    user: User,
    *,
    patient_id: uuid.UUID | None = None,
    professional_id: uuid.UUID | None = None,
    date_from: datetime.datetime | None = None,
    date_to: datetime.datetime | None = None,
    status_filter: AppointmentStatus | None = None,
) -> list[dict]:
    query = db.query(Appointment).filter(_tenant_scope_filter(user), Appointment.deleted_at.is_(None))
    visibility = _visibility_filter(user)
    if visibility is not None:
        query = query.filter(visibility)
    if patient_id is not None:
        patient_service.get_patient_or_404(db, user, patient_id)
        query = query.filter(Appointment.patient_id == patient_id)
    if professional_id is not None:
        query = query.filter(Appointment.professional_id == professional_id)
    if date_from is not None:
        query = query.filter(Appointment.scheduled_end >= date_from)
    if date_to is not None:
        query = query.filter(Appointment.scheduled_start <= date_to)
    if status_filter is not None:
        query = query.filter(Appointment.status == status_filter)

    appointments = query.order_by(Appointment.scheduled_start).all()
    return _enrich(db, appointments)


def update_appointment(db: Session, user: User, appointment_id: uuid.UUID, payload: AppointmentUpdateRequest) -> dict:
    appointment = get_appointment_or_404(db, user, appointment_id)
    if appointment.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only scheduled/confirmed appointments can be edited")

    professional_id = payload.professional_id or appointment.professional_id
    start = payload.scheduled_start or appointment.scheduled_start
    end = payload.scheduled_end or appointment.scheduled_end
    if end <= start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scheduled_end must be after scheduled_start")

    professional = _validate_professional(db, user, professional_id)

    if (professional.id, start, end) != (appointment.professional_id, appointment.scheduled_start, appointment.scheduled_end):
        if _has_conflict(db, professional.id, start, end, exclude_id=appointment.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This professional already has an appointment in this time range",
            )

    appointment.professional_id = professional.id
    appointment.scheduled_start = start
    appointment.scheduled_end = end
    if payload.notes is not None:
        appointment.notes = payload.notes

    audit_service.record(
        db, actor_user_id=user.id, action="appointment_updated", entity_type="appointment", entity_id=appointment.id
    )
    db.commit()
    db.refresh(appointment)
    patient = db.get(Patient, appointment.patient_id)
    return _to_response_dict(appointment, patient.name if patient else "?", professional.name)


def confirm_appointment(db: Session, user: User, appointment_id: uuid.UUID) -> dict:
    appointment = get_appointment_or_404(db, user, appointment_id)
    if appointment.status != AppointmentStatus.SCHEDULED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only scheduled appointments can be confirmed")
    appointment.status = AppointmentStatus.CONFIRMED
    audit_service.record(
        db, actor_user_id=user.id, action="appointment_confirmed", entity_type="appointment", entity_id=appointment.id
    )
    db.commit()
    db.refresh(appointment)
    return _enrich(db, [appointment])[0]


def cancel_appointment(
    db: Session, user: User, appointment_id: uuid.UUID, *, reason: CancellationReason, notes: str | None
) -> dict:
    appointment = get_appointment_or_404(db, user, appointment_id)
    if appointment.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only scheduled/confirmed appointments can be cancelled")
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancellation_reason = reason
    appointment.status_notes = notes
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="appointment_cancelled",
        entity_type="appointment",
        entity_id=appointment.id,
        after={"reason": reason.value},
    )
    db.commit()
    db.refresh(appointment)
    return _enrich(db, [appointment])[0]


def _notify_consecutive_no_shows(db: Session, appointment: Appointment) -> None:
    """Seção 32.3 — alerta ao supervisor/admin quando um paciente acumula faltas
    consecutivas (limiar de 2, escolha de engenharia já que o PRD não especifica um número)."""
    recent = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == appointment.patient_id,
            Appointment.deleted_at.is_(None),
            Appointment.status.in_((AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW)),
        )
        .order_by(Appointment.scheduled_start.desc())
        .limit(CONSECUTIVE_NO_SHOW_THRESHOLD)
        .all()
    )
    if len(recent) < CONSECUTIVE_NO_SHOW_THRESHOLD:
        return
    if not all(a.status == AppointmentStatus.NO_SHOW for a in recent):
        return

    if appointment.clinic_id is None:
        return  # individual accounts have no supervisor to alert

    patient = db.get(Patient, appointment.patient_id)
    recipients = (
        db.query(User)
        .filter(User.clinic_id == appointment.clinic_id, User.user_type.in_((UserType.CLINIC_ADMIN, UserType.SUPERVISOR)))
        .all()
    )
    for recipient in recipients:
        notification_service.create_notification(
            db,
            recipient_user_id=recipient.id,
            actor_user_id=None,
            notification_type="attendance_alert",
            message=f"{patient.name if patient else 'Paciente'} acumulou {CONSECUTIVE_NO_SHOW_THRESHOLD} faltas consecutivas",
            entity_type="patient",
            entity_id=appointment.patient_id,
        )


def mark_no_show(
    db: Session, user: User, appointment_id: uuid.UUID, *, reason: CancellationReason | None, notes: str | None
) -> dict:
    appointment = get_appointment_or_404(db, user, appointment_id)
    if appointment.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only scheduled/confirmed appointments can be marked as no-show")
    appointment.status = AppointmentStatus.NO_SHOW
    appointment.cancellation_reason = reason
    appointment.status_notes = notes
    audit_service.record(
        db, actor_user_id=user.id, action="appointment_no_show", entity_type="appointment", entity_id=appointment.id
    )
    _notify_consecutive_no_shows(db, appointment)
    db.commit()
    db.refresh(appointment)
    return _enrich(db, [appointment])[0]


def link_session_to_appointment(db: Session, user: User, appointment_id: uuid.UUID, session_id: uuid.UUID) -> None:
    """Seção 32.2 — marcar uma sessão agendada como "realizada" abre o Novo Atendimento;
    ao salvar esse atendimento, o compromisso é vinculado e passa para 'realizada'."""
    appointment = get_appointment_or_404(db, user, appointment_id)
    if appointment.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only scheduled/confirmed appointments can be completed")
    appointment.status = AppointmentStatus.COMPLETED
    appointment.session_id = session_id
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="appointment_completed",
        entity_type="appointment",
        entity_id=appointment.id,
        after={"session_id": str(session_id)},
    )
    db.flush()


def soft_delete_appointment(db: Session, user: User, appointment_id: uuid.UUID, reason: str | None = None) -> None:
    appointment = get_appointment_or_404(db, user, appointment_id)
    appointment.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    appointment.deleted_by = user.id
    appointment.deletion_reason = reason
    audit_service.record(
        db, actor_user_id=user.id, action="appointment_deleted", entity_type="appointment", entity_id=appointment.id
    )
    db.commit()


def list_deleted_appointments(db: Session, user: User) -> list[Appointment]:
    return (
        db.query(Appointment)
        .filter(_tenant_scope_filter(user), Appointment.deleted_at.isnot(None))
        .order_by(Appointment.deleted_at.desc())
        .all()
    )


def restore_appointment(db: Session, user: User, appointment_id: uuid.UUID) -> Appointment:
    from app.core.config import get_settings

    settings = get_settings()
    appointment = get_appointment_or_404(db, user, appointment_id, include_deleted=True)
    if appointment.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Appointment is not deleted")
    retention_deadline = appointment.deleted_at + datetime.timedelta(days=settings.DELETED_DATA_RETENTION_DAYS)
    if datetime.datetime.now(datetime.timezone.utc) > retention_deadline:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Retention period has expired")

    appointment.deleted_at = None
    appointment.deleted_by = None
    appointment.deletion_reason = None
    audit_service.record(
        db, actor_user_id=user.id, action="appointment_restored", entity_type="appointment", entity_id=appointment.id
    )
    db.commit()
    db.refresh(appointment)
    return appointment


def attendance_rate(db: Session, user: User, patient_id: uuid.UUID) -> dict:
    """Seção 32.3 — indicador de taxa de comparecimento por paciente."""
    patient_service.get_patient_or_404(db, user, patient_id)
    completed = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.deleted_at.is_(None),
            Appointment.status == AppointmentStatus.COMPLETED,
        )
        .count()
    )
    no_show = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.deleted_at.is_(None),
            Appointment.status == AppointmentStatus.NO_SHOW,
        )
        .count()
    )
    total = completed + no_show
    rate = round((completed / total) * 100, 1) if total > 0 else None
    return {
        "patient_id": patient_id,
        "completed_count": completed,
        "no_show_count": no_show,
        "attendance_rate_pct": rate,
    }


def _ics_datetime(value: datetime.datetime) -> str:
    return value.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _appointment_to_vevent(appointment: dict) -> str:
    now = _ics_datetime(datetime.datetime.now(datetime.timezone.utc))
    lines = [
        "BEGIN:VEVENT",
        f"UID:{appointment['id']}@behaviorhub",
        f"DTSTAMP:{now}",
        f"DTSTART:{_ics_datetime(appointment['scheduled_start'])}",
        f"DTEND:{_ics_datetime(appointment['scheduled_end'])}",
        f"SUMMARY:Atendimento - {appointment['patient_name']}",
        f"DESCRIPTION:Profissional: {appointment['professional_name']} | Status: {appointment['status'].value}",
        "STATUS:" + ("CANCELLED" if appointment["status"] == AppointmentStatus.CANCELLED else "CONFIRMED"),
        "END:VEVENT",
    ]
    return "\r\n".join(lines)


def build_ics_calendar(appointments: list[dict]) -> str:
    """Seção 32.2 — exportação de ICS (sincronização unidirecional com Google
    Calendar/Outlook); integração bidirecional fica para fase futura."""
    body = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Behavior Hub//Agenda//PT",
        "CALSCALE:GREGORIAN",
    ]
    for appointment in appointments:
        body.append(_appointment_to_vevent(appointment))
    body.append("END:VCALENDAR")
    return "\r\n".join(body) + "\r\n"
