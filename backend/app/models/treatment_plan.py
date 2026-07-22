import datetime
import uuid

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ApplierType, ObjectivePriority, ObjectiveStatus, TreatmentArea


class TreatmentPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 13.1 — cada paciente possui uma página única de Treatment Plan."""

    __tablename__ = "treatment_plans"
    __table_args__ = (UniqueConstraint("patient_id", name="uq_treatment_plans_patient_id"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    objectives: Mapped[list["Objective"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="Objective.created_at"
    )
    attachments: Mapped[list["TreatmentPlanAttachment"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="TreatmentPlanAttachment.uploaded_at"
    )


class Objective(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Seção 13.1/13.2 — objetivo do plano, organizado por área."""

    __tablename__ = "objectives"

    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("treatment_plans.id"), nullable=False, index=True)
    area: Mapped[TreatmentArea] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategies: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ObjectiveStatus] = mapped_column(default=ObjectiveStatus.NOT_STARTED, nullable=False)
    priority: Mapped[ObjectivePriority] = mapped_column(default=ObjectivePriority.MEDIUM, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Addendum v2.1, RF-05 — rascunho gerado a partir do texto de um PDF já
    # anexado à área (RF-04); ai_reviewed_at é preenchido no próprio instante da
    # criação, já que o objetivo só é persistido depois da ação explícita de
    # "Salvar" do profissional (nunca há publicação automática sem revisão).
    ai_generated: Mapped[bool] = mapped_column(default=False, nullable=False)
    ai_source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("treatment_plan_attachments.id"), nullable=True
    )
    # Addendum v2.1, RF-06 — quando o objetivo vem da ativação de um rascunho de
    # plano gerado a partir de uma Avaliação Padronizada, em vez de um PDF (RF-05).
    ai_source_assessment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assessments.id"), nullable=True)
    ai_reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Addendum v3.0, RF-24 — quando um objetivo é marcado como "Dominado", ele
    # entra em acompanhamento de manutenção (reteste periódico automático) e
    # generalização (registro de onde a habilidade já foi testada), em vez de
    # simplesmente desaparecer. Estende o próprio Objective (Seção 18 do PRD),
    # sem tabela paralela, conforme instrução explícita do addendum.
    maintenance_check_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    generalization_contexts: Mapped[list | None] = mapped_column(JSON, nullable=True)

    plan: Mapped["TreatmentPlan"] = relationship(back_populates="objectives")
    comments: Mapped[list["ObjectiveComment"]] = relationship(
        back_populates="objective", cascade="all, delete-orphan", order_by="ObjectiveComment.created_at"
    )
    training_links: Mapped[list["ObjectiveTraining"]] = relationship(
        back_populates="objective", cascade="all, delete-orphan"
    )


class TreatmentPlanAttachment(Base, UUIDPrimaryKeyMixin):
    """Addendum v2.1, RF-04 — PDF anexado a uma área específica da grade
    multidisciplinar (ex.: avaliação externa, plano em papel), sem relação
    com nenhum Objective individual."""

    __tablename__ = "treatment_plan_attachments"

    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("treatment_plans.id"), nullable=False, index=True)
    area: Mapped[TreatmentArea] = mapped_column(nullable=False)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plan: Mapped["TreatmentPlan"] = relationship(back_populates="attachments")


class ObjectiveComment(Base, UUIDPrimaryKeyMixin):
    """Seção 13.1 — comentários e atualizações por objetivo."""

    __tablename__ = "objective_comments"

    objective_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("objectives.id"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    objective: Mapped["Objective"] = relationship(back_populates="comments")


class ObjectiveTraining(Base, UUIDPrimaryKeyMixin):
    """Seção 18/27 — vínculo opcional Objective N—N Training, usado nos filtros de Reports."""

    __tablename__ = "objective_trainings"
    __table_args__ = (UniqueConstraint("objective_id", "training_id", name="uq_objective_trainings"),)

    objective_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("objectives.id"), nullable=False, index=True)
    training_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trainings.id"), nullable=False, index=True)

    objective: Mapped["Objective"] = relationship(back_populates="training_links")


class ObjectiveApplier(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Addendum v3.0, RF-25 — pai/cuidador (ou profissional) marcado como
    aplicador de um objetivo específico, geralmente de generalização em casa
    (liga diretamente ao RF-24). O registro do "apliquei hoje" em si não vira
    uma tabela nova — reaproveita AuditLog (action="objective_applied"),
    mesmo mecanismo já usado pelo histórico do objetivo (Seção 13.1)."""

    __tablename__ = "objective_appliers"
    __table_args__ = (
        UniqueConstraint("objective_id", "applier_user_id", name="uq_objective_appliers_objective_user"),
    )

    objective_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("objectives.id"), nullable=False, index=True)
    applier_type: Mapped[ApplierType] = mapped_column(nullable=False)
    applier_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    added_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
