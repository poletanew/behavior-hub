import uuid

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClinicPermissionSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 17.1 — permissões marcadas como "Configurável" na tabela de RBAC do
    PRD. Uma linha por clínica; contas individuais não usam esta tabela (o
    próprio profissional individual já tem acesso total ao seu tenant)."""

    __tablename__ = "clinic_permission_settings"
    __table_args__ = (UniqueConstraint("clinic_id", name="uq_clinic_permission_settings_clinic_id"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)

    # "Cadastrar paciente": Profissional — Configurável (Seção 17.1)
    professionals_can_create_patients: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # "Registrar sessão": Supervisor — Configurável
    supervisors_can_register_sessions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # "Editar objetivo de outra área": Admin clínica / Supervisor — Configurável
    supervisors_can_edit_any_objective_area: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admins_can_edit_any_objective_area: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # "Restaurar Deleted Data": Supervisor — Configurável
    supervisors_can_restore_deleted_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # "Gerar convite": Supervisor — Configurável
    supervisors_can_generate_invitations: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
