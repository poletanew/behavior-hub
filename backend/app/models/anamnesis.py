import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Anamnesis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Addendum v3.0, RF-21 — formulário de admissão (um por paciente),
    aplicado no cadastro ou logo depois. Estruturado em campos fixos (em vez
    de um JSON livre) porque, diferente de Assessment.raw_scores — cujos
    domínios variam por protocolo —, as seções da anamnese são sempre as
    mesmas, então um schema fixo é mais simples de validar e exibir."""

    __tablename__ = "anamneses"
    __table_args__ = (UniqueConstraint("patient_id", name="uq_anamneses_patient_id"),)

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    birth_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    developmental_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    developmental_milestones: Mapped[str | None] = mapped_column(Text, nullable=True)
    family_history: Mapped[str | None] = mapped_column(Text, nullable=True)
