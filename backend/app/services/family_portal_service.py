import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.enums import AppointmentStatus, ReportSummaryStatus, UserType
from app.models.family_access import FamilyAccess, FamilyMessage
from app.models.patient import Patient
from app.models.report_summary import ReportSummary
from app.models.resource import Resource
from app.models.resource_link import ResourceLink
from app.models.treatment_plan import Objective, ObjectiveApplier, ObjectiveTraining, TreatmentPlan
from app.models.user import User
from app.services import audit_service, report_service, white_label_service
from app.services.resource_link_service import _to_response as _resource_link_response

# Seção 17.2 — o Family Portal nunca reaproveita os gates normais de paciente
# (patient_service.get_patient_or_404 rejeita contas FAMILY de propósito).
# Todo acesso aqui passa exclusivamente pela whitelist explícita de
# FamilyAccess: cada método abaixo confere a flag correspondente antes de
# devolver qualquer dado, nunca por omissão.


def _require_family(user: User) -> None:
    if user.user_type != UserType.FAMILY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a family account")


def _get_active_access(db: Session, family_user: User, patient_id: uuid.UUID) -> FamilyAccess:
    _require_family(family_user)
    access = (
        db.query(FamilyAccess)
        .filter(FamilyAccess.patient_id == patient_id, FamilyAccess.family_user_id == family_user.id)
        .first()
    )
    if access is None or not access.is_active():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return access


def _require_category(access: FamilyAccess, field: str) -> None:
    if not getattr(access, field):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This data category is not shared with you")


def list_my_accesses(db: Session, family_user: User) -> list[dict]:
    _require_family(family_user)
    rows = (
        db.query(FamilyAccess, Patient)
        .join(Patient, FamilyAccess.patient_id == Patient.id)
        .filter(FamilyAccess.family_user_id == family_user.id, FamilyAccess.revoked_at.is_(None))
        .all()
    )
    return [
        {
            "patient_id": patient.id,
            "patient_name": patient.name,
            "can_view_evolution_charts": access.can_view_evolution_charts,
            "can_view_upcoming_appointments": access.can_view_upcoming_appointments,
            "can_view_team_guidance": access.can_view_team_guidance,
            "can_view_home_materials": access.can_view_home_materials,
            "can_use_messaging": access.can_use_messaging,
        }
        for access, patient in rows
    ]


def get_branding(db: Session, family_user: User, patient_id: uuid.UUID) -> dict:
    """Seção 32.9 — a marca (logo/cor/nome) não é uma categoria de dados
    clínicos da whitelist (Seção 17.2); basta o responsável ter algum acesso
    ativo a este paciente para ver a identidade visual da clínica dele."""
    _get_active_access(db, family_user, patient_id)
    patient = db.get(Patient, patient_id)
    clinic_id = patient.clinic_id if patient is not None else None
    return white_label_service.get_branding_for_clinic(db, clinic_id)


def get_evolution(db: Session, family_user: User, patient_id: uuid.UUID) -> dict:
    access = _get_active_access(db, family_user, patient_id)
    _require_category(access, "can_view_evolution_charts")

    rows = report_service._fetch_rows(
        db, patient_id, date_from=None, date_to=None, training_id=None, category_id=None, professional_id=None
    )
    return {
        "line": report_service.build_line_series(rows),
        "radar": report_service.build_radar_data(rows),
        "cumulative": report_service.build_cumulative_data(rows),
    }


def list_upcoming_appointments(db: Session, family_user: User, patient_id: uuid.UUID) -> list[dict]:
    access = _get_active_access(db, family_user, patient_id)
    _require_category(access, "can_view_upcoming_appointments")

    now = datetime.datetime.now(datetime.timezone.utc)
    rows = (
        db.query(Appointment, User.name)
        .join(User, Appointment.professional_id == User.id)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.deleted_at.is_(None),
            Appointment.scheduled_start >= now,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
        )
        .order_by(Appointment.scheduled_start)
        .all()
    )
    return [
        {
            "id": appointment.id,
            "professional_name": professional_name,
            "scheduled_start": appointment.scheduled_start,
            "scheduled_end": appointment.scheduled_end,
            "status": appointment.status.value,
        }
        for appointment, professional_name in rows
    ]


def list_team_guidance(db: Session, family_user: User, patient_id: uuid.UUID) -> list[ReportSummary]:
    """Seção 29.6 — a família só vê orientações já aprovadas pelo profissional
    (nunca um rascunho em edição), reaproveitando o mesmo status usado em
    Reports (Seção 14.5)."""
    access = _get_active_access(db, family_user, patient_id)
    _require_category(access, "can_view_team_guidance")

    return (
        db.query(ReportSummary)
        .filter(ReportSummary.patient_id == patient_id, ReportSummary.status == ReportSummaryStatus.APPROVED)
        .order_by(ReportSummary.period_end.desc())
        .all()
    )


def list_home_materials(db: Session, family_user: User, patient_id: uuid.UUID) -> list[dict]:
    """Seção 29.6 — materiais de casa: mesma agregação direto+via-treino de
    resource_link_service.list_links_for_objective, mas restrita aos
    objetivos ativos do paciente (sem reusar o gate de patient_service)."""
    access = _get_active_access(db, family_user, patient_id)
    _require_category(access, "can_view_home_materials")

    plan = db.query(TreatmentPlan).filter(TreatmentPlan.patient_id == patient_id).first()
    if plan is None:
        return []

    objective_ids = [
        row[0]
        for row in db.query(Objective.id)
        .filter(Objective.plan_id == plan.id, Objective.deleted_at.is_(None))
        .all()
    ]
    if not objective_ids:
        return []

    direct = (
        db.query(ResourceLink, Resource)
        .join(Resource, ResourceLink.resource_id == Resource.id)
        .filter(ResourceLink.objective_id.in_(objective_ids), Resource.deleted_at.is_(None))
        .all()
    )
    training_ids = [
        row[0]
        for row in db.query(ObjectiveTraining.training_id)
        .filter(ObjectiveTraining.objective_id.in_(objective_ids))
        .all()
    ]
    via_training = []
    if training_ids:
        via_training = (
            db.query(ResourceLink, Resource)
            .join(Resource, ResourceLink.resource_id == Resource.id)
            .filter(ResourceLink.training_id.in_(training_ids), Resource.deleted_at.is_(None))
            .all()
        )

    combined: dict[uuid.UUID, tuple[ResourceLink, Resource]] = {}
    for link, resource in direct + via_training:
        existing = combined.get(resource.id)
        if existing is None or link.relevance_score > existing[0].relevance_score:
            combined[resource.id] = (link, resource)

    ordered = sorted(combined.values(), key=lambda pair: -pair[0].relevance_score)
    return [_resource_link_response(link, resource) for link, resource in ordered]


def list_messages(db: Session, family_user: User, patient_id: uuid.UUID) -> list[dict]:
    access = _get_active_access(db, family_user, patient_id)
    _require_category(access, "can_use_messaging")
    return _messages_with_sender_name(db, patient_id)


def post_message(db: Session, family_user: User, patient_id: uuid.UUID, body: str) -> dict:
    access = _get_active_access(db, family_user, patient_id)
    _require_category(access, "can_use_messaging")

    message = FamilyMessage(patient_id=patient_id, sender_user_id=family_user.id, body=body)
    db.add(message)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=family_user.id,
        action="family_message_sent",
        entity_type="family_message",
        entity_id=message.id,
    )
    db.commit()
    db.refresh(message)
    return {
        "id": message.id,
        "patient_id": message.patient_id,
        "sender_user_id": message.sender_user_id,
        "sender_name": family_user.name,
        "body": message.body,
        "created_at": message.created_at,
    }


def _messages_with_sender_name(db: Session, patient_id: uuid.UUID) -> list[dict]:
    rows = (
        db.query(FamilyMessage, User.name)
        .join(User, FamilyMessage.sender_user_id == User.id)
        .filter(FamilyMessage.patient_id == patient_id)
        .order_by(FamilyMessage.created_at)
        .all()
    )
    return [
        {
            "id": message.id,
            "patient_id": message.patient_id,
            "sender_user_id": message.sender_user_id,
            "sender_name": sender_name,
            "body": message.body,
            "created_at": message.created_at,
        }
        for message, sender_name in rows
    ]


def list_messages_for_team(db: Session, staff_user: User, patient_id: uuid.UUID) -> list[dict]:
    """Lado da equipe (não-família): usado pela página do paciente para
    visualizar/enviar mensagens no mesmo canal. Reaproveita o gate normal de
    paciente já que quem chama aqui nunca é uma conta FAMILY."""
    from app.services import patient_service

    patient_service.get_patient_or_404(db, staff_user, patient_id)
    return _messages_with_sender_name(db, patient_id)


def post_message_for_team(db: Session, staff_user: User, patient_id: uuid.UUID, body: str) -> dict:
    from app.services import patient_service

    patient_service.get_patient_or_404(db, staff_user, patient_id)

    message = FamilyMessage(patient_id=patient_id, sender_user_id=staff_user.id, body=body)
    db.add(message)
    db.flush()
    audit_service.record(
        db,
        actor_user_id=staff_user.id,
        action="family_message_sent",
        entity_type="family_message",
        entity_id=message.id,
    )
    db.commit()
    db.refresh(message)
    return {
        "id": message.id,
        "patient_id": message.patient_id,
        "sender_user_id": message.sender_user_id,
        "sender_name": staff_user.name,
        "body": message.body,
        "created_at": message.created_at,
    }


def list_applier_objectives(db: Session, family_user: User, patient_id: uuid.UUID) -> list[dict]:
    """Addendum v3.0, RF-25 — objetivos em que este responsável foi marcado
    como aplicador (ObjectiveTraining/treatment_plan_service.add_applier),
    com indicação se "apliquei hoje" já foi registrado. Diferente das demais
    seções do Family Portal, RF-25 não depende de nenhuma flag de
    FamilyAccess: ser aplicador de um objetivo específico já é, em si, a
    autorização concedida objetivo a objetivo pelo profissional — mas ainda
    exige acesso ativo ao paciente (_get_active_access), para não vazar dados
    de um paciente cujo consentimento já foi revogado."""
    _get_active_access(db, family_user, patient_id)

    rows = (
        db.query(ObjectiveApplier, Objective)
        .join(Objective, ObjectiveApplier.objective_id == Objective.id)
        .join(TreatmentPlan, Objective.plan_id == TreatmentPlan.id)
        .filter(
            ObjectiveApplier.applier_user_id == family_user.id,
            TreatmentPlan.patient_id == patient_id,
            Objective.deleted_at.is_(None),
        )
        .all()
    )
    today = datetime.date.today()
    result = []
    for _applier, objective in rows:
        applied_today = (
            db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "objective",
                AuditLog.entity_id == objective.id,
                AuditLog.action == "objective_applied",
                AuditLog.actor_user_id == family_user.id,
                func.date(AuditLog.timestamp) == today,
            )
            .first()
            is not None
        )
        result.append(
            {"objective_id": objective.id, "title": objective.title, "area": objective.area, "applied_today": applied_today}
        )
    return result


def record_objective_application(
    db: Session, family_user: User, patient_id: uuid.UUID, objective_id: uuid.UUID, notes: str | None
) -> dict:
    """Addendum v3.0, RF-25 — "registrar 'apliquei hoje'... isso aparece no
    histórico do objetivo para o profissional ver": reaproveita o AuditLog
    (mesmo mecanismo de treatment_plan_service.get_history), sem tabela nova."""
    _get_active_access(db, family_user, patient_id)

    applier = (
        db.query(ObjectiveApplier)
        .filter(ObjectiveApplier.objective_id == objective_id, ObjectiveApplier.applier_user_id == family_user.id)
        .first()
    )
    if applier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You are not registered as an applier for this objective")

    objective = db.get(Objective, objective_id)
    plan = db.get(TreatmentPlan, objective.plan_id) if objective else None
    if objective is None or objective.deleted_at is not None or plan is None or plan.patient_id != patient_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objective not found")

    audit_service.record(
        db,
        actor_user_id=family_user.id,
        action="objective_applied",
        entity_type="objective",
        entity_id=objective.id,
        after={"applier": "parent", "notes": notes},
    )
    db.commit()
    return {"objective_id": objective.id, "applied_at": datetime.datetime.now(datetime.timezone.utc)}
