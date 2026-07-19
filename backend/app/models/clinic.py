import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, StripeBillingMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SubscriptionPlan, SubscriptionStatus


class Clinic(Base, UUIDPrimaryKeyMixin, TimestampMixin, StripeBillingMixin):
    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_clinics_owner_user_id"), nullable=True
    )
    subscription_plan: Mapped[SubscriptionPlan] = mapped_column(
        default=SubscriptionPlan.FREE, nullable=False
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        default=SubscriptionStatus.NONE, nullable=False
    )

    # Seção 32.9 — White-label (Enterprise): logo, cor de destaque e nome exibido
    # em relatórios exportados e no Family Portal. Nunca altera a marca dentro do
    # próprio produto (Seção 23 permanece a identidade oficial do sistema).
    white_label_logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    white_label_brand_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    white_label_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="clinic", foreign_keys="User.clinic_id"
    )

    @property
    def has_paid_access(self) -> bool:
        """Seção 8.3 — "nunca confiar apenas no frontend": uma assinatura
        atrasada/cancelada nunca mantém os direitos do plano pago, mesmo que
        subscription_plan ainda esteja com o rótulo antigo."""
        return self.subscription_status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)
