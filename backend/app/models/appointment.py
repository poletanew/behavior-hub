import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AppointmentStatus, CancellationReason


class Appointment(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Seção 32.2 — Agenda/Scheduling: sessão agendada, diferente da sessão já registrada
    (ClinicalSession)."""

    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "(clinic_id IS NOT NULL AND individual_owner_id IS NULL) OR "
            "(clinic_id IS NULL AND individual_owner_id IS NOT NULL)",
            name="ck_appointments_single_tenant_owner",
        ),
    )

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    professional_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)

    scheduled_start: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(default=AppointmentStatus.SCHEDULED, nullable=False)
    cancellation_reason: Mapped[CancellationReason | None] = mapped_column(nullable=True)
    status_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reminder_sent_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
