import datetime
import uuid

from sqlalchemy import JSON, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AssessmentProtocol


class Assessment(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Seção 27.2/30 — aplicação de um protocolo de avaliação padronizada.

    `raw_scores` é uma lista de objetos por domínio (Seção 30.1.1):
    {domain_code, domain_label, raw_value, max_value, normalized_pct}. Um
    schema fixo no banco não funcionaria aqui, já que cada protocolo tem seus
    próprios domínios/escalas — o JSON evita reformular a tabela a cada novo
    protocolo (ProtocolDefinition em app/services/assessment_protocols.py)."""

    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("patient_id", "protocol", "applied_date", name="uq_assessments_patient_protocol_date"),
    )

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    professional_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    protocol: Mapped[AssessmentProtocol] = mapped_column(nullable=False, index=True)
    applied_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    raw_scores: Mapped[list] = mapped_column(JSON, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
