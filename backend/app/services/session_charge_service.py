import csv
import datetime
import io
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import PaymentStatus, UserType
from app.models.patient import Patient
from app.models.session import ClinicalSession
from app.models.session_charge import SessionCharge
from app.models.user import User
from app.schemas.session_charge import SessionChargeCreateRequest, SessionChargeUpdateRequest
from app.services import audit_service, patient_service, session_service
from app.services.plan_service import current_plan

BILLING_PLANS = ("premium", "enterprise")


def _require_billing_plan(user: User) -> None:
    """Seção 32.10 — "Recurso de plano Premium/Enterprise"."""
    if current_plan(user) not in BILLING_PLANS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session billing is available only on the Premium or Enterprise plan",
        )


def _require_admin(user: User) -> None:
    """Mesma restrição usada para gestão de assinatura/Stripe (billing_service):
    dado financeiro sensível, só administrador de clínica ou tenant individual."""
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to manage session billing")


def _to_response(charge: SessionCharge, patient: Patient, session: ClinicalSession) -> dict:
    return {
        "id": charge.id,
        "session_id": charge.session_id,
        "patient_id": charge.patient_id,
        "patient_name": patient.name,
        "session_date": session.occurred_at,
        "amount": float(charge.amount),
        "due_date": charge.due_date,
        "payment_status": charge.payment_status,
        "paid_at": charge.paid_at,
        "notes": charge.notes,
        "created_by_user_id": charge.created_by_user_id,
        "created_at": charge.created_at,
    }


def create_charge(db: Session, user: User, session_id: uuid.UUID, payload: SessionChargeCreateRequest) -> dict:
    _require_admin(user)
    _require_billing_plan(user)

    session = session_service.get_session_or_404(db, user, session_id)
    patient = patient_service.get_patient_or_404(db, user, session.patient_id)

    existing = db.query(SessionCharge).filter(SessionCharge.session_id == session_id).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This session already has a charge")

    charge = SessionCharge(
        session_id=session.id,
        patient_id=patient.id,
        clinic_id=user.clinic_id,
        individual_owner_id=None if user.clinic_id else user.id,
        amount=payload.amount,
        due_date=payload.due_date,
        notes=payload.notes,
        created_by_user_id=user.id,
    )
    db.add(charge)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="session_charge_created",
        entity_type="session_charge",
        entity_id=charge.id,
        after={"session_id": str(session.id), "amount": payload.amount},
    )
    db.commit()
    db.refresh(charge)
    return _to_response(charge, patient, session)


def get_charge_for_session(db: Session, user: User, session_id: uuid.UUID) -> dict | None:
    session = session_service.get_session_or_404(db, user, session_id)
    patient = patient_service.get_patient_or_404(db, user, session.patient_id)
    charge = db.query(SessionCharge).filter(SessionCharge.session_id == session_id).first()
    if charge is None:
        return None
    return _to_response(charge, patient, session)


def _get_charge_or_404(db: Session, user: User, charge_id: uuid.UUID) -> tuple[SessionCharge, Patient, ClinicalSession]:
    charge = db.get(SessionCharge, charge_id)
    if charge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session charge not found")
    patient = patient_service.get_patient_or_404(db, user, charge.patient_id)
    session = session_service.get_session_or_404(db, user, charge.session_id)
    return charge, patient, session


def update_charge(db: Session, user: User, charge_id: uuid.UUID, payload: SessionChargeUpdateRequest) -> dict:
    _require_admin(user)
    charge, patient, session = _get_charge_or_404(db, user, charge_id)

    before = {"amount": float(charge.amount), "due_date": str(charge.due_date), "notes": charge.notes}
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(charge, field, value)

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="session_charge_updated",
        entity_type="session_charge",
        entity_id=charge.id,
        before=before,
        after=updates,
    )
    db.commit()
    db.refresh(charge)
    return _to_response(charge, patient, session)


def update_status(db: Session, user: User, charge_id: uuid.UUID, new_status: PaymentStatus) -> dict:
    _require_admin(user)
    charge, patient, session = _get_charge_or_404(db, user, charge_id)

    before_status = charge.payment_status
    charge.payment_status = new_status
    if new_status == PaymentStatus.PAID and charge.paid_at is None:
        charge.paid_at = datetime.datetime.now(datetime.timezone.utc)
    elif new_status != PaymentStatus.PAID:
        charge.paid_at = None

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="session_charge_status_updated",
        entity_type="session_charge",
        entity_id=charge.id,
        before={"payment_status": before_status.value},
        after={"payment_status": new_status.value},
    )
    db.commit()
    db.refresh(charge)
    return _to_response(charge, patient, session)


def list_charges_for_patient(db: Session, user: User, patient_id: uuid.UUID) -> list[dict]:
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    rows = (
        db.query(SessionCharge, ClinicalSession)
        .join(ClinicalSession, SessionCharge.session_id == ClinicalSession.id)
        .filter(SessionCharge.patient_id == patient_id)
        .order_by(ClinicalSession.occurred_at.desc())
        .all()
    )
    return [_to_response(charge, patient, session) for charge, session in rows]


def _tenant_scope_filter(user: User):
    if user.clinic_id is not None:
        return SessionCharge.clinic_id == user.clinic_id
    return SessionCharge.individual_owner_id == user.id


def export_csv(
    db: Session,
    user: User,
    *,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> str:
    """Seção 32.10 — "exportação para o financeiro da clínica"."""
    _require_admin(user)
    _require_billing_plan(user)

    query = (
        db.query(SessionCharge, Patient, ClinicalSession)
        .join(Patient, SessionCharge.patient_id == Patient.id)
        .join(ClinicalSession, SessionCharge.session_id == ClinicalSession.id)
        .filter(_tenant_scope_filter(user))
    )
    if date_from is not None:
        query = query.filter(ClinicalSession.occurred_at >= date_from)
    if date_to is not None:
        query = query.filter(
            ClinicalSession.occurred_at <= datetime.datetime.combine(date_to, datetime.time.max)
        )
    rows = query.order_by(ClinicalSession.occurred_at).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Data da sessão", "Paciente", "Valor", "Vencimento", "Status", "Pago em"])
    for charge, patient, session in rows:
        writer.writerow(
            [
                session.occurred_at.strftime("%Y-%m-%d %H:%M"),
                patient.name,
                f"{charge.amount:.2f}",
                charge.due_date.strftime("%Y-%m-%d") if charge.due_date else "",
                charge.payment_status.value,
                charge.paid_at.strftime("%Y-%m-%d %H:%M") if charge.paid_at else "",
            ]
        )
    return buffer.getvalue()
