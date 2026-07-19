import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FamilyAccess(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 29.6 / 17.2 — grant de acesso do Portal da Família a um paciente.

    Escopo definido por whitelist de campos (nunca por blacklist, Seção 17.2):
    cada categoria de dado só é exibida ao responsável se a respectiva flag
    abaixo estiver explicitamente True. Qualquer categoria nova adicionada ao
    sistema no futuro deve nascer aqui como uma nova flag default False, nunca
    exposta por omissão."""

    __tablename__ = "family_accesses"
    __table_args__ = (
        UniqueConstraint("patient_id", "family_user_id", name="uq_family_accesses_patient_family_user"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    family_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    granted_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Seção 17.2 — "acesso de responsáveis exige consentimento explícito e
    # registrado do titular/responsável legal do paciente".
    consent_given_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    can_view_evolution_charts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_view_upcoming_appointments: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_view_team_guidance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_view_home_materials: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_use_messaging: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Seção 17.2 — "Revogação... deve ser imediata e registrada em audit log,
    # com encerramento de sessões ativas do responsável" (ver User.token_version).
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    def is_active(self) -> bool:
        return self.revoked_at is None


class FamilyMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 29.6 — canal de mensagens entre a família e a equipe, sem
    threading no MVP (lista simples ordenada por data)."""

    __tablename__ = "family_messages"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
