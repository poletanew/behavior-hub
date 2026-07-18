import datetime

from app.db.session import SessionLocal
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.patient import Patient
from app.services import notification_service
from app.tasks.celery_app import celery_app

REMINDER_WINDOW_HOURS = 24


@celery_app.task(name="app.tasks.reminders.send_appointment_reminders")
def send_appointment_reminders() -> int:
    """Seção 32.2 — lembrete automático para o profissional sobre atendimentos
    agendados nas próximas 24h. Envio para o responsável (quando aplicável) fica
    fora de escopo nesta etapa: o produto ainda não tem um Family Portal/conta de
    responsável para endereçar — apenas a notificação in-app do profissional é
    enviada por aqui; um provedor de e-mail real é uma decisão de configuração
    futura (mesma lacuna documentada para 2FA/e-mail e convites)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    window_end = now + datetime.timedelta(hours=REMINDER_WINDOW_HOURS)

    db = SessionLocal()
    sent = 0
    try:
        upcoming = (
            db.query(Appointment)
            .filter(
                Appointment.deleted_at.is_(None),
                Appointment.reminder_sent_at.is_(None),
                Appointment.status.in_((AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED)),
                Appointment.scheduled_start >= now,
                Appointment.scheduled_start <= window_end,
            )
            .all()
        )
        for appointment in upcoming:
            patient = db.get(Patient, appointment.patient_id)
            notification_service.create_notification(
                db,
                recipient_user_id=appointment.professional_id,
                actor_user_id=None,
                notification_type="appointment_reminder",
                message=(
                    f"Atendimento com {patient.name if patient else 'paciente'} em "
                    f"{appointment.scheduled_start.strftime('%d/%m/%Y %H:%M')}"
                ),
                entity_type="appointment",
                entity_id=appointment.id,
            )
            appointment.reminder_sent_at = now
            sent += 1
        db.commit()
    finally:
        db.close()

    return sent
