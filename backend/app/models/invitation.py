import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InvitationStatus, Specialty, UserType


class Invitation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 7.1 — convites de profissionais."""

    __tablename__ = "invitations"

    # Nullable porque um profissional individual (sem clinic_id) também pode
    # convidar um responsável (Family Portal) para um paciente seu.
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    specialty: Mapped[Specialty | None] = mapped_column(nullable=True)
    # Seção 17.1 — permite convidar profissionais, supervisores ou (Seção 29.6) responsáveis.
    role: Mapped[UserType] = mapped_column(default=UserType.PROFESSIONAL, nullable=False)
    # Seção 29.6 — obrigatório apenas quando role == FAMILY: o paciente ao qual o
    # responsável convidado terá acesso restrito e consentido.
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)

    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(default=InvitationStatus.PENDING, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    accepted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
