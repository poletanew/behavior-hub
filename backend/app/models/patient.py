import datetime
import uuid

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AssignmentPermission, PatientStatus, SchoolShift


class Patient(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint(
            "(clinic_id IS NOT NULL AND individual_owner_id IS NULL) OR "
            "(clinic_id IS NULL AND individual_owner_id IS NOT NULL)",
            name="ck_patients_single_tenant_owner",
        ),
    )

    # Tenant isolation (Seção 17): exactly one of clinic_id / individual_owner_id is set.
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clinics.id"), nullable=True, index=True
    )
    individual_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    guardian_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Addendum v2.1, RF-03 — dados pessoais adicionais (Seção 17.2/LGPD: mesmo
    # tratamento de acesso já aplicado a diagnosis, sem uma camada de
    # criptografia por campo separada — texto simples como os demais campos
    # sensíveis deste modelo).
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    school_shift: Mapped[SchoolShift | None] = mapped_column(nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[PatientStatus] = mapped_column(default=PatientStatus.ACTIVE, nullable=False)

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    assignments: Mapped[list["PatientAssignment"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class PatientAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Seção 7.3 — compartilhamento de pacientes entre profissionais."""

    __tablename__ = "patient_assignments"
    __table_args__ = (
        CheckConstraint(
            "patient_id IS NOT NULL AND professional_id IS NOT NULL",
            name="ck_patient_assignments_required_fields",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    permission: Mapped[AssignmentPermission] = mapped_column(
        default=AssignmentPermission.EDIT_SESSIONS, nullable=False
    )

    patient: Mapped["Patient"] = relationship(back_populates="assignments")
