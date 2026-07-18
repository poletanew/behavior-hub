import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SubscriptionPlan, Specialty, UserStatus, UserType


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_type: Mapped[UserType] = mapped_column(nullable=False)
    specialty: Mapped[Specialty | None] = mapped_column(nullable=True)
    status: Mapped[UserStatus] = mapped_column(default=UserStatus.ACTIVE, nullable=False)

    # Tenant isolation (Seção 6.2 / 17): a user belongs either to a clinic OR is an
    # individual tenant (clinic_id is NULL). Every clinical query must filter by this.
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clinics.id", use_alter=True, name="fk_users_clinic_id"), nullable=True, index=True
    )

    # Individual professionals (no clinic) carry their own subscription plan.
    subscription_plan: Mapped[SubscriptionPlan | None] = mapped_column(nullable=True)

    terms_accepted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    clinic: Mapped["Clinic | None"] = relationship(  # noqa: F821
        back_populates="users", foreign_keys=[clinic_id]
    )

    def is_individual_tenant(self) -> bool:
        return self.clinic_id is None

    def tenant_key(self) -> str:
        """Unique identifier of the isolation boundary this user belongs to."""
        return f"clinic:{self.clinic_id}" if self.clinic_id else f"individual:{self.id}"
