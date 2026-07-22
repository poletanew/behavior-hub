import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Room(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Addendum v3.0, RF-26 — sala física de atendimento, vinculável a um
    Appointment para checagem de conflito de horário (mesmo padrão já usado
    para o profissional, Seção 32.2)."""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint(
            "(clinic_id IS NOT NULL AND individual_owner_id IS NULL) OR "
            "(clinic_id IS NULL AND individual_owner_id IS NOT NULL)",
            name="ck_rooms_single_tenant_owner",
        ),
    )

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
