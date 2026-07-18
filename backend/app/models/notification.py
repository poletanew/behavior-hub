import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 32.6 — Central de Notificações: painel único que consolida comentários
    novos e menções (@) em objetivos do plano de tratamento. Cada notificação leva
    diretamente ao registro de origem (Seção 32.6/32.13)."""

    __tablename__ = "notifications"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)  # "comment" | "mention"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)  # "objective"
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    read_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
