import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SessionTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 32.4 — modelo de atendimento com o conjunto de treinos padrão,
    reutilizável em um clique para iniciar uma nova sessão."""

    __tablename__ = "session_templates"

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    # Um template pode ser específico de um paciente (rotina recorrente) ou genérico da clínica.
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    trainings: Mapped[list["SessionTemplateTraining"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="SessionTemplateTraining.sequence"
    )


class SessionTemplateTraining(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "session_template_trainings"

    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("session_templates.id"), nullable=False, index=True)
    training_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trainings.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    template: Mapped["SessionTemplate"] = relationship(back_populates="trainings")
