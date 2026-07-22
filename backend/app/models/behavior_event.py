import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BehaviorIntensity


class BehaviorEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Addendum v3.0, RF-18 — registro de comportamento-alvo no modelo ABC
    (Antecedente → Comportamento → Consequência), independente das tentativas
    de treino, sempre ligado a um atendimento específico."""

    __tablename__ = "behavior_events"

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    antecedent: Mapped[str] = mapped_column(Text, nullable=False)
    behavior: Mapped[str] = mapped_column(Text, nullable=False)
    consequence: Mapped[str] = mapped_column(Text, nullable=False)
    frequency_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intensity: Mapped[BehaviorIntensity | None] = mapped_column(nullable=True)

    occurred_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
