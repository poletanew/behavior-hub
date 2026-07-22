import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased

from app.models.anamnesis import Anamnesis
from app.models.assessment import Assessment
from app.models.audit_log import AuditLog
from app.models.behavior_event import BehaviorEvent
from app.models.checklist import ChecklistResponse
from app.models.enums import UserType
from app.models.patient import Patient
from app.models.reinforcer import Reinforcer
from app.models.report_summary import ReportSummary
from app.models.session import ClinicalSession
from app.models.treatment_plan import Objective, TreatmentPlan, TreatmentPlanAttachment
from app.models.user import User
from app.services import patient_service

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

# RF-14 — categorias de ação patient-scoped reaproveitadas da mesma cobertura
# já usada pela Timeline Clínica (Seção 29.2): sessões, plano de tratamento,
# anexos/uploads (RF-04), atribuições e avaliações. Trials individuais não
# entram — o addendum fala em "sessões", não em cada tentativa isolada.
_PATIENT_ENTITY_TYPES = (
    "patient",
    "session",
    "objective",
    "treatment_plan_attachment",
    "patient_assignment",
    "assessment",
    "report_summary",
    "behavior_event",
    "reinforcer",
    "anamnesis",
    "checklist_response",
)


def list_audit_logs(
    db: Session,
    user: User,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    date_from: datetime.datetime | None = None,
    date_to: datetime.datetime | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> list[dict]:
    """Seção 17/21 — auditoria completa, restrita a administradores e escopada
    por tenant (via o tenant do usuário que praticou a ação).

    Limitação conhecida: ações de sistema sem ator (ex.: purga automática da
    Seção 16.2, actor_user_id nulo) não aparecem nesta consulta escopada por
    tenant — ficam registradas no banco, mas não têm um usuário para derivar o
    tenant. Isso é aceitável para o núcleo da Fase 3; um painel de auditoria
    "de sistema" fica fora deste escopo.
    """
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view audit logs")

    actor = aliased(User)
    query = db.query(AuditLog, actor.name).join(actor, AuditLog.actor_user_id == actor.id)

    if user.clinic_id is not None:
        query = query.filter(actor.clinic_id == user.clinic_id)
    else:
        query = query.filter(actor.id == user.id)

    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if actor_user_id is not None:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)
    if date_from is not None:
        query = query.filter(AuditLog.timestamp >= date_from)
    if date_to is not None:
        query = query.filter(AuditLog.timestamp <= date_to)

    limit = min(limit, MAX_LIMIT)
    rows = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return [
        {
            "id": entry.id,
            "actor_user_id": entry.actor_user_id,
            "actor_name": actor_name,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "before": entry.before,
            "after": entry.after,
            "timestamp": entry.timestamp,
        }
        for entry, actor_name in rows
    ]


def _patient_scoped_entity_ids(db: Session, patient: Patient) -> dict[str, list[uuid.UUID]]:
    """Resolve, para cada entity_type patient-scoped, os IDs que pertencem a
    este paciente — incluindo registros já excluídos (soft delete), já que
    "exclusões" e "restaurações" fazem parte do próprio critério de aceite do
    RF-14."""
    sessions = [row[0] for row in db.query(ClinicalSession.id).filter(ClinicalSession.patient_id == patient.id).all()]

    plan = db.query(TreatmentPlan).filter(TreatmentPlan.patient_id == patient.id).first()
    objectives: list[uuid.UUID] = []
    attachments: list[uuid.UUID] = []
    if plan is not None:
        objectives = [row[0] for row in db.query(Objective.id).filter(Objective.plan_id == plan.id).all()]
        attachments = [
            row[0] for row in db.query(TreatmentPlanAttachment.id).filter(TreatmentPlanAttachment.plan_id == plan.id).all()
        ]

    assessments = [row[0] for row in db.query(Assessment.id).filter(Assessment.patient_id == patient.id).all()]
    reports = [row[0] for row in db.query(ReportSummary.id).filter(ReportSummary.patient_id == patient.id).all()]
    behavior_events = [
        row[0] for row in db.query(BehaviorEvent.id).filter(BehaviorEvent.patient_id == patient.id).all()
    ]
    reinforcers = [row[0] for row in db.query(Reinforcer.id).filter(Reinforcer.patient_id == patient.id).all()]
    anamneses = [row[0] for row in db.query(Anamnesis.id).filter(Anamnesis.patient_id == patient.id).all()]
    checklist_responses = [
        row[0] for row in db.query(ChecklistResponse.id).filter(ChecklistResponse.patient_id == patient.id).all()
    ]

    return {
        "patient": [patient.id],
        "session": sessions,
        "objective": objectives,
        "treatment_plan_attachment": attachments,
        "patient_assignment": [patient.id],
        "assessment": assessments,
        "report_summary": reports,
        "behavior_event": behavior_events,
        "reinforcer": reinforcers,
        "anamnesis": anamneses,
        "checklist_response": checklist_responses,
    }


def get_patient_audit_trail(db: Session, user: User, patient_id: uuid.UUID) -> list[dict]:
    """RF-14 — "clicar no nome do paciente abre uma linha do tempo consolidada
    com todas as ações registradas por qualquer profissional sobre aquele
    paciente". Reaproveita a mesma cobertura de entidades já usada pela
    Timeline Clínica (Seção 29.2), mas devolvendo o formato de auditoria
    (autor/ação/timestamp) em vez de rótulos clínicos."""
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view audit logs")

    patient = patient_service.get_patient_or_404(db, user, patient_id, include_deleted=True)
    entity_ids_by_type = _patient_scoped_entity_ids(db, patient)

    actor = aliased(User)
    query = db.query(AuditLog, actor.name).join(actor, AuditLog.actor_user_id == actor.id)
    if user.clinic_id is not None:
        query = query.filter(actor.clinic_id == user.clinic_id)
    else:
        query = query.filter(actor.id == user.id)

    conditions = [
        (AuditLog.entity_type == entity_type) & AuditLog.entity_id.in_(ids)
        for entity_type, ids in entity_ids_by_type.items()
        if ids
    ]
    if not conditions:
        return []

    query = query.filter(AuditLog.entity_type.in_(_PATIENT_ENTITY_TYPES), or_(*conditions))
    rows = query.order_by(AuditLog.timestamp.asc()).all()

    return [
        {
            "id": entry.id,
            "actor_user_id": entry.actor_user_id,
            "actor_name": actor_name,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "before": entry.before,
            "after": entry.after,
            "timestamp": entry.timestamp,
        }
        for entry, actor_name in rows
    ]
