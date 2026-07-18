import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TrainingVisibility


class TrainingCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 12.1 — categorias da Training Library (ex.: Comunicação, Social, Autonomia, Motor)."""

    __tablename__ = "training_categories"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    trainings: Mapped[list["Training"]] = relationship(back_populates="category")


class Training(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 12.2 — estrutura do treino."""

    __tablename__ = "trainings"

    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("training_categories.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    discriminative_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_hierarchy: Mapped[str | None] = mapped_column(Text, nullable=True)
    mastery_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_age_range: Mapped[str | None] = mapped_column(String(60), nullable=True)

    visibility: Mapped[TrainingVisibility] = mapped_column(
        default=TrainingVisibility.SYSTEM, nullable=False
    )
    # System trainings are protected from deletion (Seção 12.1). Custom trainings
    # belong to a clinic or an individual professional.
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    category: Mapped["TrainingCategory"] = relationship(back_populates="trainings")

    def is_system_protected(self) -> bool:
        return self.visibility == TrainingVisibility.SYSTEM
