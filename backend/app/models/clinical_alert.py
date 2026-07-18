import datetime
import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ClinicalAlertType


class ClinicalAlert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 29.1/29.9 — alerta clínico acionável gerado por uma regra automática.

    Um alerta "ativo" (resolved_at IS NULL) representa uma condição que ainda
    é verdadeira da última vez em que foi recalculada; ao deixar de ser
    verdadeira, é marcado como resolvido em vez de apagado (mantém histórico).
    Um par (objective_id, alert_type) nunca tem mais de um alerta ativo ao
    mesmo tempo — dedup garantido pelo índice único parcial abaixo (NULL não
    conta como valor igual em um UNIQUE comum, por isso o índice parcial)."""

    __tablename__ = "clinical_alerts"
    __table_args__ = (
        Index(
            "uq_clinical_alerts_active_objective_type",
            "objective_id",
            "alert_type",
            unique=True,
            postgresql_where=text("resolved_at IS NULL"),
        ),
    )

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    objective_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("objectives.id"), nullable=False, index=True)

    alert_type: Mapped[ClinicalAlertType] = mapped_column(nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    triggered_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
