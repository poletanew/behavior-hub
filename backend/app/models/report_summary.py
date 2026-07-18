import datetime
import uuid

from sqlalchemy import JSON, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ReportSummaryStatus


class ReportSummary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 14.5 — resumo do relatório, editável e versionado para auditoria.

    Fase 2 gera um rascunho determinístico a partir dos dados agregados (sem
    chamar nenhuma API de IA externa ainda — ver Seção 28.6/README). O campo
    `generated_by` deixa isso explícito para a interface e para auditoria.
    """

    __tablename__ = "report_summaries"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    period_start: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    period_end: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReportSummaryStatus] = mapped_column(default=ReportSummaryStatus.DRAFT, nullable=False)
    generated_by: Mapped[str] = mapped_column(default="rule_based_draft", nullable=False)
    data_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
