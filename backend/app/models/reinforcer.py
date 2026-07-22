import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Reinforcer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Addendum v3.0, RF-19 — cadastro de reforçadores por paciente (o que
    funciona para motivá-lo), reaproveitado pelo RF de sugestão de IA (Seção
    12.1/29.1 do PRD) e pelo gráfico de reforçadores (RF-34)."""

    __tablename__ = "reinforcers"

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    effectiveness_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    usages: Mapped[list["SessionReinforcer"]] = relationship(back_populates="reinforcer")


class SessionReinforcer(Base, UUIDPrimaryKeyMixin):
    """Addendum v3.0, RF-19 — registro de qual reforçador foi usado em uma
    sessão específica, com nota rápida de efetividade daquele uso."""

    __tablename__ = "session_reinforcers"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    reinforcer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reinforcers.id"), nullable=False, index=True)
    effectiveness_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    used_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reinforcer: Mapped["Reinforcer"] = relationship(back_populates="usages")
