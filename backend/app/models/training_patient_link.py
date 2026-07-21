import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TrainingLinkStatus


class TrainingPatientLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Addendum v2.1, RF-10 — vincula um treino da Biblioteca a um paciente
    específico ("treino prescrito"), sem precisar esperar a próxima sessão
    para escolher esse treino manualmente na tela de Novo Atendimento."""

    __tablename__ = "training_patient_links"
    __table_args__ = (
        UniqueConstraint("training_id", "patient_id", name="uq_training_patient_link"),
    )

    training_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trainings.id"), nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    linked_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    linked_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TrainingLinkStatus] = mapped_column(default=TrainingLinkStatus.PRESCRIBED, nullable=False)
