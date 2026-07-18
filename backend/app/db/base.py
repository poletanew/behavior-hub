import datetime
import uuid

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )


class TimestampMixin:
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """Section 16 — soft delete only, never immediate physical deletion."""

    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deletion_reason: Mapped[str | None] = mapped_column(nullable=True)


class StripeBillingMixin:
    """Seção 8.3 — campos de assinatura Stripe, compartilhados por Clinic (tenant
    de clínica) e User (tenant individual), já que cada um carrega seu próprio
    subscription_plan hoje.

    Não inclui subscription_status/subscription_plan aqui: esses dependem dos
    enums de app.models.enums, e este módulo (app.db.base) é importado por
    app.models.appointment antes que o pacote app.models termine de
    inicializar — importar app.models.enums a partir daqui reintroduziria
    esse pacote no meio da própria inicialização (import circular). Cada
    modelo concreto (Clinic, User) declara subscription_status e
    has_paid_access diretamente."""

    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    subscription_current_period_end: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
