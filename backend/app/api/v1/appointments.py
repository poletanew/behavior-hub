import datetime
import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import AppointmentStatus
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AppointmentStatusChangeRequest,
    AppointmentUpdateRequest,
    AttendanceRateResponse,
)
from app.services import appointment_service

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    patient_id: uuid.UUID | None = None,
    professional_id: uuid.UUID | None = None,
    date_from: datetime.datetime | None = None,
    date_to: datetime.datetime | None = None,
    appointment_status: AppointmentStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.2 — visão de calendário por profissional, paciente ou clínica."""
    return appointment_service.list_appointments(
        db,
        user,
        patient_id=patient_id,
        professional_id=professional_id,
        date_from=date_from,
        date_to=date_to,
        status_filter=appointment_status,
    )


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return appointment_service.create_appointment(db, user, payload)


@router.get("/export.ics")
def export_ics(
    professional_id: uuid.UUID | None = None,
    patient_id: uuid.UUID | None = None,
    date_from: datetime.datetime | None = None,
    date_to: datetime.datetime | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.2 — exportação de ICS para Google Calendar/Outlook."""
    appointments = appointment_service.list_appointments(
        db, user, patient_id=patient_id, professional_id=professional_id, date_from=date_from, date_to=date_to
    )
    calendar = appointment_service.build_ics_calendar(appointments)
    return Response(
        content=calendar,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=agenda.ics"},
    )


@router.get("/attendance-rate/{patient_id}", response_model=AttendanceRateResponse)
def attendance_rate(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 32.3 — indicador de taxa de comparecimento por paciente."""
    return appointment_service.attendance_rate(db, user, patient_id)


@router.get("/{appointment_id}/export.ics")
def export_single_ics(appointment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    enriched = appointment_service.get_enriched_appointment(db, user, appointment_id)
    calendar = appointment_service.build_ics_calendar([enriched])
    return Response(
        content=calendar,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=atendimento-{appointment_id}.ics"},
    )


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return appointment_service.update_appointment(db, user, appointment_id, payload)


@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
def confirm_appointment(appointment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return appointment_service.confirm_appointment(db, user, appointment_id)


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.3 — registrar cancelamento com motivo (paciente, clínica, profissional, força maior)."""
    return appointment_service.cancel_appointment(db, user, appointment_id, reason=payload.reason, notes=payload.notes)


@router.post("/{appointment_id}/no-show", response_model=AppointmentResponse)
def mark_no_show(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 32.3 — registrar não comparecimento; alerta o supervisor em faltas consecutivas."""
    return appointment_service.mark_no_show(db, user, appointment_id, reason=payload.reason, notes=payload.notes)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(appointment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    appointment_service.soft_delete_appointment(db, user, appointment_id)
