import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import WaitlistStatus
from app.models.user import User
from app.models.waitlist_entry import WaitlistEntry
from app.schemas.patient import PatientCreateRequest
from app.schemas.waitlist import WaitlistConvertRequest, WaitlistEntryCreateRequest, WaitlistEntryUpdateRequest
from app.services import audit_service, patient_service, rbac_service


def _tenant_scope_filter(user: User):
    if user.clinic_id is not None:
        return WaitlistEntry.clinic_id == user.clinic_id
    return WaitlistEntry.individual_owner_id == user.id


def _require_permission(db: Session, user: User) -> None:
    """Seção 17.1 — mesma regra de "Cadastrar paciente": a lista de espera é
    um pré-cadastro, então segue a mesma permissão configurável."""
    if not rbac_service.can_create_patient(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to manage the waitlist")


def create_entry(db: Session, user: User, payload: WaitlistEntryCreateRequest) -> WaitlistEntry:
    _require_permission(db, user)

    entry = WaitlistEntry(
        clinic_id=user.clinic_id,
        individual_owner_id=None if user.clinic_id else user.id,
        name=payload.name,
        birth_date=payload.birth_date,
        guardian_name=payload.guardian_name,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        notes=payload.notes,
        created_by_user_id=user.id,
    )
    db.add(entry)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="waitlist_entry_created",
        entity_type="waitlist_entry",
        entity_id=entry.id,
        after={"name": entry.name},
    )
    db.commit()
    db.refresh(entry)
    return entry


def list_entries(db: Session, user: User, *, status_filter: WaitlistStatus | None = None) -> list[WaitlistEntry]:
    query = db.query(WaitlistEntry).filter(_tenant_scope_filter(user))
    if status_filter is not None:
        query = query.filter(WaitlistEntry.status == status_filter)
    return query.order_by(WaitlistEntry.created_at).all()


def _get_entry_or_404(db: Session, user: User, entry_id: uuid.UUID) -> WaitlistEntry:
    entry = db.query(WaitlistEntry).filter(WaitlistEntry.id == entry_id, _tenant_scope_filter(user)).first()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found")
    return entry


def update_entry(db: Session, user: User, entry_id: uuid.UUID, payload: WaitlistEntryUpdateRequest) -> WaitlistEntry:
    _require_permission(db, user)
    entry = _get_entry_or_404(db, user, entry_id)
    if entry.status != WaitlistStatus.WAITING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only waiting entries can be edited")

    before = {"name": entry.name}
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(entry, field, value)

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="waitlist_entry_updated",
        entity_type="waitlist_entry",
        entity_id=entry.id,
        before=before,
        after=updates,
    )
    db.commit()
    db.refresh(entry)
    return entry


def discard_entry(db: Session, user: User, entry_id: uuid.UUID) -> WaitlistEntry:
    _require_permission(db, user)
    entry = _get_entry_or_404(db, user, entry_id)
    if entry.status != WaitlistStatus.WAITING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only waiting entries can be discarded")

    entry.status = WaitlistStatus.DISCARDED
    audit_service.record(
        db, actor_user_id=user.id, action="waitlist_entry_discarded", entity_type="waitlist_entry", entity_id=entry.id
    )
    db.commit()
    db.refresh(entry)
    return entry


def convert_entry(db: Session, user: User, entry_id: uuid.UUID, payload: WaitlistConvertRequest) -> WaitlistEntry:
    """Seção 32.11 — "conversão em paciente completo sem redigitação": os
    campos já preenchidos na triagem (nome, responsável, notas) viram o
    paciente diretamente, sem o profissional ter que digitar tudo de novo."""
    _require_permission(db, user)
    entry = _get_entry_or_404(db, user, entry_id)
    if entry.status != WaitlistStatus.WAITING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only waiting entries can be converted")

    birth_date = payload.birth_date or entry.birth_date
    if birth_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="birth_date is required to convert a waitlist entry into a patient",
        )

    patient = patient_service.create_patient(
        db,
        user,
        PatientCreateRequest(
            name=entry.name,
            birth_date=birth_date,
            guardian_name=entry.guardian_name,
            diagnosis=payload.diagnosis,
            notes=entry.notes,
        ),
    )

    entry.status = WaitlistStatus.CONVERTED
    entry.converted_patient_id = patient.id
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="waitlist_entry_converted",
        entity_type="waitlist_entry",
        entity_id=entry.id,
        after={"converted_patient_id": str(patient.id)},
    )
    db.commit()
    db.refresh(entry)
    return entry
