import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
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

    # Addendum v2.1, RF-13 — Importação em Lote de Pacientes fica oculta do menu
    # principal por padrão; liberável manualmente por clínicas Enterprise que
    # precisem migrar de outro sistema, sem exigir novo deploy.
    bulk_import_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Seção 29.1 — limiares dos Alertas Clínicos Inteligentes. Padrão de fábrica
    # conforme o PRD; configuráveis por clínica apenas no plano Enterprise
    # (aplicado em clinical_alert_service.update_thresholds).
    no_collection_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    regression_window_sessions: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    regression_drop_pp: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    stagnation_session_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    stagnation_band_pp: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    fading_session_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    fading_independence_pct: Mapped[int] = mapped_column(Integer, default=80, nullable=False)

    # Seção 29.1 (Fase 4b) — limiar da sugestão de "objetivo pode ser considerado
    # dominado" (Seção 29.9), mesma lógica de configuração das demais.
    mastery_suggestion_session_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    mastery_suggestion_accuracy_pct: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
