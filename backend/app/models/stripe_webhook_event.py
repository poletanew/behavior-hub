from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StripeWebhookEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 28.4 — chave de deduplicação por evento: todo evento Stripe recebido
    é registrado aqui antes de ser processado; um `stripe_event_id` repetido
    (reentrega do Stripe) é ignorado."""

    __tablename__ = "stripe_webhook_events"
    __table_args__ = (UniqueConstraint("stripe_event_id", name="uq_stripe_webhook_events_event_id"),)

    stripe_event_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
