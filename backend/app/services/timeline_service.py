import datetime
import uuid

from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.audit_log import AuditLog
from app.models.patient import Patient
from app.models.report_summary import ReportSummary
from app.models.session import ClinicalSession
from app.models.treatment_plan import Objective, TreatmentPlan
from app.models.user import User

OBJECTIVE_ACTIONS = ("objective_created", "objective_updated", "objective_deleted", "objective_restored")


def _session_entries(db: Session, patient: Patient) -> list[dict]:
    """Seção 29.2 — "sessões realizadas"."""
    sessions = (
        db.query(ClinicalSession)
        .filter(ClinicalSession.patient_id == patient.id, ClinicalSession.deleted_at.is_(None))
        .all()
    )
    if not sessions:
        return []

    professional_ids = {s.professional_id for s in sessions}
    professionals = {u.id: u.name for u in db.query(User).filter(User.id.in_(professional_ids)).all()}

    return [
        {
            "id": session.id,
            "event_type": "session_completed",
            "occurred_at": session.occurred_at,
            "label": f"Atendimento realizado com {professionals.get(session.professional_id, 'profissional removido')}",
            "source_type": "session",
            "source_id": session.id,
        }
        for session in sessions
    ]


def _objective_entries(db: Session, patient: Patient) -> list[dict]:
    """Seção 29.2 — "alterações do plano de tratamento" e "marcos de evolução"
    (objetivo dominado é tratado como um marco de evolução distinto, mesmo
    vindo do mesmo evento de auditoria objective_updated)."""
    plan = db.query(TreatmentPlan).filter(TreatmentPlan.patient_id == patient.id).first()
    if plan is None:
        return []

    objective_ids = [row[0] for row in db.query(Objective.id).filter(Objective.plan_id == plan.id).all()]
    if not objective_ids:
        return []

    titles = {o.id: o.title for o in db.query(Objective).filter(Objective.id.in_(objective_ids)).all()}
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "objective", AuditLog.entity_id.in_(objective_ids), AuditLog.action.in_(OBJECTIVE_ACTIONS))
        .all()
    )

    entries = []
    for log in logs:
        title = titles.get(log.entity_id, "Objetivo")
        if log.action == "objective_created":
            entries.append(
                {
                    "id": log.id,
                    "event_type": "objective_created",
                    "occurred_at": log.timestamp,
                    "label": f"Objetivo criado: {title}",
                    "source_type": "objective",
                    "source_id": log.entity_id,
                }
            )
        elif log.action == "objective_updated":
            before_status = (log.before or {}).get("status")
            after_status = (log.after or {}).get("status")
            if after_status == "mastered" and before_status != "mastered":
                entries.append(
                    {
                        "id": log.id,
                        "event_type": "objective_mastered",
                        "occurred_at": log.timestamp,
                        "label": f"Objetivo dominado: {title}",
                        "source_type": "objective",
                        "source_id": log.entity_id,
                    }
                )
            else:
                entries.append(
                    {
                        "id": log.id,
                        "event_type": "objective_updated",
                        "occurred_at": log.timestamp,
                        "label": f"Objetivo atualizado: {title}",
                        "source_type": "objective",
                        "source_id": log.entity_id,
                    }
                )
        elif log.action == "objective_deleted":
            entries.append(
                {
                    "id": log.id,
                    "event_type": "objective_deleted",
                    "occurred_at": log.timestamp,
                    "label": f"Objetivo excluído: {title}",
                    "source_type": "objective",
                    "source_id": log.entity_id,
                }
            )
        elif log.action == "objective_restored":
            entries.append(
                {
                    "id": log.id,
                    "event_type": "objective_restored",
                    "occurred_at": log.timestamp,
                    "label": f"Objetivo restaurado: {title}",
                    "source_type": "objective",
                    "source_id": log.entity_id,
                }
            )
    return entries


def _assignment_entries(db: Session, patient: Patient) -> list[dict]:
    """Seção 29.2 — "mudanças de profissional responsável"."""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "patient_assignment", AuditLog.entity_id == patient.id)
        .all()
    )
    if not logs:
        return []

    professional_ids: set[uuid.UUID] = set()
    for log in logs:
        payload = log.after or log.before or {}
        raw_id = payload.get("professional_id")
        if raw_id:
            professional_ids.add(uuid.UUID(raw_id))
    professionals = {u.id: u.name for u in db.query(User).filter(User.id.in_(professional_ids)).all()}

    entries = []
    for log in logs:
        payload = log.after or log.before or {}
        raw_id = payload.get("professional_id")
        professional_name = professionals.get(uuid.UUID(raw_id), "profissional removido") if raw_id else "profissional removido"
        if log.action == "patient_assignment_upserted":
            label = f"{professional_name} vinculado ao paciente"
        else:
            label = f"{professional_name} desvinculado do paciente"
        entries.append(
            {
                "id": log.id,
                "event_type": log.action,
                "occurred_at": log.timestamp,
                "label": label,
                "source_type": "patient",
                "source_id": patient.id,
            }
        )
    return entries


def _report_entries(db: Session, patient: Patient) -> list[dict]:
    """Seção 29.2 — "relatórios gerados". Uma entrada por versão de resumo
    (não por edição), já que o objeto ReportSummary já é o registro
    canônico de "este relatório existe" — cada versão é um evento distinto."""
    reports = db.query(ReportSummary).filter(ReportSummary.patient_id == patient.id).all()
    return [
        {
            "id": report.id,
            "event_type": "report_generated",
            "occurred_at": report.created_at,
            "label": (
                f"Relatório gerado (versão {report.version}, período de "
                f"{report.period_start.strftime('%d/%m/%Y')} a {report.period_end.strftime('%d/%m/%Y')})"
            ),
            "source_type": "report_summary",
            "source_id": patient.id,
        }
        for report in reports
    ]


def _assessment_entries(db: Session, patient: Patient) -> list[dict]:
    """Seção 29.2 — "avaliações aplicadas"."""
    assessments = (
        db.query(Assessment)
        .filter(Assessment.patient_id == patient.id, Assessment.deleted_at.is_(None))
        .all()
    )
    return [
        {
            "id": assessment.id,
            "event_type": "assessment_applied",
            "occurred_at": datetime.datetime.combine(assessment.applied_date, datetime.time.min, tzinfo=datetime.timezone.utc),
            "label": f"Avaliação {assessment.protocol.value.upper().replace('_', '-')} aplicada",
            "source_type": "assessment",
            "source_id": assessment.id,
        }
        for assessment in assessments
    ]


def get_patient_timeline(db: Session, patient: Patient) -> list[dict]:
    """Seção 29.2/AC-18 — timeline única consolidando, em ordem cronológica e
    sem duplicados, os eventos clínicos do paciente.

    Intercorrências registradas ainda não existem no produto (nenhum modelo
    de dados para elas hoje) — não alimentam a timeline nesta etapa; ver
    README para o registro dessa lacuna."""
    entries = (
        _session_entries(db, patient)
        + _objective_entries(db, patient)
        + _assignment_entries(db, patient)
        + _report_entries(db, patient)
        + _assessment_entries(db, patient)
    )
    entries.sort(key=lambda e: (e["occurred_at"], str(e["id"])))
    return entries
