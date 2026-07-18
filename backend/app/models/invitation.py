import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InvitationStatus, Specialty


class Invitation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 7.1 — convites de profissionais."""

    __tablename__ = "invitations"

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    specialty: Mapped[Specialty | None] = mapped_column(nullable=True)

    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(default=InvitationStatus.PENDING, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    accepted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
