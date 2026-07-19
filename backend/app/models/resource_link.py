import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResourceLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 29.7 — vínculo estruturado recurso↔treino ou recurso↔objetivo,
    dependência bloqueante da Biblioteca Inteligente. Populado manualmente
    (tagueamento) pelo profissional, não por inferência automática de IA —
    "não há dado histórico suficiente para a IA inferir a relação sozinha no
    lançamento" (Seção 29.7)."""

    __tablename__ = "resource_links"
    __table_args__ = (
        CheckConstraint(
            "(training_id IS NOT NULL AND objective_id IS NULL) OR "
            "(training_id IS NULL AND objective_id IS NOT NULL)",
            name="ck_resource_links_single_target",
        ),
        CheckConstraint("relevance_score BETWEEN 1 AND 5", name="ck_resource_links_relevance_score_range"),
        Index(
            "uq_resource_links_resource_training",
            "resource_id",
            "training_id",
            unique=True,
            postgresql_where=text("training_id IS NOT NULL"),
        ),
        Index(
            "uq_resource_links_resource_objective",
            "resource_id",
            "objective_id",
            unique=True,
            postgresql_where=text("objective_id IS NOT NULL"),
        ),
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"), nullable=False, index=True)
    training_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("trainings.id"), nullable=True, index=True)
    objective_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("objectives.id"), nullable=True, index=True)
    relevance_score: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
