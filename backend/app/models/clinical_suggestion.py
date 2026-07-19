import datetime
import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SuggestionStatus, SuggestionType


class ClinicalSuggestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 29.1 (Fase 4b) — recomendação clínica gerada por regra, sempre
    editável pelo profissional (nunca aplicada automaticamente).

    Ao contrário do ClinicalAlert (que se re-abre sempre que a condição volta
    a ser verdadeira), uma sugestão é gerada no máximo uma vez por
    (objective_id, suggestion_type) ou (patient_id, training_id,
    suggestion_type) — uma vez decidida (aprovada ou descartada) pelo
    profissional, essa decisão é respeitada e a sugestão não reaparece. Os
    índices únicos abaixo garantem isso independente do status."""

    __tablename__ = "clinical_suggestions"
    __table_args__ = (
        Index(
            "uq_clinical_suggestions_objective_type",
            "objective_id",
            "suggestion_type",
            unique=True,
            postgresql_where=text("objective_id IS NOT NULL"),
        ),
        Index(
            "uq_clinical_suggestions_patient_training_type",
            "patient_id",
            "training_id",
            "suggestion_type",
            unique=True,
            postgresql_where=text("training_id IS NOT NULL"),
        ),
    )

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    objective_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("objectives.id"), nullable=True, index=True)
    training_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("trainings.id"), nullable=True, index=True)

    suggestion_type: Mapped[SuggestionType] = mapped_column(nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[SuggestionStatus] = mapped_column(default=SuggestionStatus.PENDING, nullable=False, index=True)

    decided_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
