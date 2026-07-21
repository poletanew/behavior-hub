import datetime
import uuid

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ResourceType, ResourceVisibility


class Resource(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Seção 15 — Recursos Terapêuticos: upload, abertura e impressão."""

    __tablename__ = "resources"

    # Tenant isolation, same pattern as Patient/Training (Seção 17).
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    suggested_age_range: Mapped[str | None] = mapped_column(String(60), nullable=True)
    resource_type: Mapped[ResourceType] = mapped_column(nullable=False)
    file_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    visibility: Mapped[ResourceVisibility] = mapped_column(default=ResourceVisibility.PRIVATE, nullable=False)

    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Addendum v2.1, RF-12 — "Criar recurso com IA"; ai_reviewed_at é preenchido
    # no instante da publicação (mesmo princípio já usado em Objective — o
    # rascunho só existe em memória até a ação explícita de publicar).
    ai_generated: Mapped[bool] = mapped_column(default=False, nullable=False)
    ai_reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
