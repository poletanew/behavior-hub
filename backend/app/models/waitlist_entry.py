import datetime
import uuid

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WaitlistStatus


class WaitlistEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 32.11 — Lista de Espera: cadastro simplificado de pacientes em
    avaliação/triagem antes da admissão formal, com campos mínimos."""

    __tablename__ = "waitlist_entries"
    __table_args__ = (
        CheckConstraint(
            "(clinic_id IS NOT NULL AND individual_owner_id IS NULL) OR "
            "(clinic_id IS NULL AND individual_owner_id IS NOT NULL)",
            name="ck_waitlist_entries_single_tenant_owner",
        ),
    )

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[WaitlistStatus] = mapped_column(default=WaitlistStatus.WAITING, nullable=False)
    converted_patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True)

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
