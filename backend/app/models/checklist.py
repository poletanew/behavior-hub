import datetime
import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CustomChecklistTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Addendum v3.0, RF-22 — construtor de checklist reutilizável: o
    profissional monta uma vez (perguntas + tipo de resposta) e reaplica em
    vários pacientes. `questions` é uma lista de
    {id, text, answer_type} — o `id` de cada pergunta é gerado na criação do
    template e referenciado pelas respostas."""

    __tablename__ = "custom_checklist_templates"

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    questions: Mapped[list] = mapped_column(JSON, nullable=False)


class ChecklistResponse(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Addendum v3.0, RF-22 — uma aplicação de um template a um paciente.
    `answers` é uma lista de {question_id, value}."""

    __tablename__ = "checklist_responses"

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("custom_checklist_templates.id"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    applied_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    answers: Mapped[list] = mapped_column(JSON, nullable=False)
    applied_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
