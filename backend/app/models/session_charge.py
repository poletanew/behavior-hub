import datetime
import uuid

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentStatus


class SessionCharge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 32.10 — Faturamento por Sessão (Billing Clínico): cobrança que a
    própria clínica emite a seus pacientes/convênios por sessão realizada.
    Complementar e sem nenhuma relação com o Stripe da assinatura SaaS
    (Seção 8) — este valor nunca é processado por um gateway de pagamento
    real, é só um registro de controle interno."""

    __tablename__ = "session_charges"
    __table_args__ = (
        CheckConstraint(
            "(clinic_id IS NOT NULL AND individual_owner_id IS NULL) OR "
            "(clinic_id IS NULL AND individual_owner_id IS NOT NULL)",
            name="ck_session_charges_single_tenant_owner",
        ),
        CheckConstraint("amount > 0", name="ck_session_charges_amount_positive"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)

    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    due_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.PENDING, nullable=False)
    paid_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
