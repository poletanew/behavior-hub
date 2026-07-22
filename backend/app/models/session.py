import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PromptLevel, SessionMediaType, TrialResult


class ClinicalSession(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Seção 11 — Atendimentos/Sessions. Named ClinicalSession to avoid clashing
    with the SQLAlchemy ORM Session class."""

    __tablename__ = "sessions"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    # Denormalized tenant key so isolation can be enforced without joining patients.
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    occurred_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Addendum v3.0, RF-20 — "Foto" (acima, campo legado de URL simples desde a
    # Fase 1) vira "Foto/Vídeo": upload real via file_service (S3/MinIO),
    # com limite de duração/tamanho por plano (Seção 8.1).
    media_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    media_type: Mapped[SessionMediaType | None] = mapped_column(nullable=True)
    media_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        # Seção 18.2 — índice composto patient_id + date em Sessions.
    )

    trainings: Mapped[list["SessionTraining"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="SessionTraining.sequence"
    )


class SessionTraining(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "session_trainings"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id"), nullable=False, index=True
    )
    training_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trainings.id"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    session: Mapped["ClinicalSession"] = relationship(back_populates="trainings")
    training: Mapped["Training"] = relationship()  # noqa: F821
    trials: Mapped[list["Trial"]] = relationship(
        back_populates="session_training",
        cascade="all, delete-orphan",
        order_by="Trial.attempt_number",
    )


class Trial(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Seção 11.3 — cada tentativa e um registro individualizado (Tentativa 1, 2, 3...)."""

    __tablename__ = "trials"
    __table_args__ = (
        UniqueConstraint(
            "session_training_id", "attempt_number", name="uq_trials_session_training_attempt"
        ),
    )

    session_training_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("session_trainings.id"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[TrialResult] = mapped_column(nullable=False)
    prompt_level: Mapped[PromptLevel] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recorded_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session_training: Mapped["SessionTraining"] = relationship(back_populates="trials")
