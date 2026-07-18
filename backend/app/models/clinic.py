import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SubscriptionPlan


class Clinic(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_clinics_owner_user_id"), nullable=True
    )
    subscription_plan: Mapped[SubscriptionPlan] = mapped_column(
        default=SubscriptionPlan.FREE, nullable=False
    )

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="clinic", foreign_keys="User.clinic_id"
    )
