import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import UserType
from app.models.patient import Patient
from app.models.resource import Resource
from app.models.treatment_plan import Objective, TreatmentPlan
from app.models.user import User
from app.services import appointment_service, patient_service, rbac_service, resource_service, treatment_plan_service

settings = get_settings()


def _require_admin(db: Session, user: User) -> None:
    """Seção 16.2/17.1 — administradores e individuais sempre podem; supervisor é Configurável."""
    if user.user_type in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        return
    if not rbac_service.can_restore_deleted_data(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access Deleted Data")


def _days_remaining(deleted_at: datetime.datetime) -> int:
    deadline = deleted_at + datetime.timedelta(days=settings.DELETED_DATA_RETENTION_DAYS)
    remaining = (deadline - datetime.datetime.now(datetime.timezone.utc)).days
    return max(remaining, 0)


def list_deleted_items(db: Session, user: User) -> list[dict]:
    """Seção 16 — visão unificada de Dados Excluídos por tenant, com contagem regressiva de 60 dias."""
    _require_admin(db, user)
    items: list[dict] = []

    for patient in patient_service.list_deleted_patients(db, user):
        items.append(
            {
                "entity_type": "patient",
                "id": patient.id,
                "label": patient.name,
                "deleted_at": patient.deleted_at,
                "deleted_by": patient.deleted_by,
                "days_remaining": _days_remaining(patient.deleted_at),
            }
        )

    tenant_filter = (Patient.clinic_id == user.clinic_id) if user.clinic_id else (Patient.individual_owner_id == user.id)
    deleted_objectives = (
        db.query(Objective, Patient.name)
        .join(TreatmentPlan, Objective.plan_id == TreatmentPlan.id)
        .join(Patient, TreatmentPlan.patient_id == Patient.id)
        .filter(Objective.deleted_at.isnot(None), tenant_filter)
        .all()
    )
    for objective, patient_name in deleted_objectives:
        items.append(
            {
                "entity_type": "objective",
                "id": objective.id,
                "label": f"{objective.title} ({patient_name})",
                "deleted_at": objective.deleted_at,
                "deleted_by": objective.deleted_by,
                "days_remaining": _days_remaining(objective.deleted_at),
            }
        )

    resource_tenant_filter = (
        (Resource.clinic_id == user.clinic_id) if user.clinic_id else (Resource.individual_owner_id == user.id)
    )
    deleted_resources = db.query(Resource).filter(Resource.deleted_at.isnot(None), resource_tenant_filter).all()
    for resource in deleted_resources:
        items.append(
            {
                "entity_type": "resource",
                "id": resource.id,
                "label": resource.title,
                "deleted_at": resource.deleted_at,
                "deleted_by": resource.deleted_by,
                "days_remaining": _days_remaining(resource.deleted_at),
            }
        )

    for appointment in appointment_service.list_deleted_appointments(db, user):
        patient = db.get(Patient, appointment.patient_id)
        items.append(
            {
                "entity_type": "appointment",
                "id": appointment.id,
                "label": f"Atendimento - {patient.name if patient else '?'} ({appointment.scheduled_start.strftime('%d/%m/%Y %H:%M')})",
                "deleted_at": appointment.deleted_at,
                "deleted_by": appointment.deleted_by,
                "days_remaining": _days_remaining(appointment.deleted_at),
            }
        )

    items.sort(key=lambda i: i["deleted_at"], reverse=True)
    return items


def restore_item(db: Session, user: User, entity_type: str, item_id: uuid.UUID):
    _require_admin(db, user)
    if entity_type == "patient":
        return patient_service.restore_patient(db, user, item_id)
    if entity_type == "objective":
        return treatment_plan_service.restore_objective(db, user, item_id)
    if entity_type == "resource":
        return resource_service.restore_resource(db, user, item_id)
    if entity_type == "appointment":
        return appointment_service.restore_appointment(db, user, item_id)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown entity type")
