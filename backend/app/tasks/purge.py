import datetime

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.patient import Patient, PatientAssignment
from app.models.report_summary import ReportSummary
from app.models.resource import Resource
from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.treatment_plan import Objective, ObjectiveComment, ObjectiveTraining, TreatmentPlan
from app.services import file_service
from app.tasks.celery_app import celery_app

settings = get_settings()


def _cutoff() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=settings.DELETED_DATA_RETENTION_DAYS
    )


def _purge_patient(db, patient: Patient) -> None:
    """Respeita a ordem de dependências (trials -> session_trainings -> sessions ->
    plano/objetivos -> atribuições -> paciente) dentro de uma transação (Seção 16.3)."""
    session_ids = [
        row[0] for row in db.query(ClinicalSession.id).filter(ClinicalSession.patient_id == patient.id).all()
    ]
    session_training_ids_subquery = (
        db.query(SessionTraining.id).filter(SessionTraining.session_id.in_(session_ids)).subquery()
    )
    db.query(Trial).filter(Trial.session_training_id.in_(session_training_ids_subquery.select())).delete(
        synchronize_session=False
    )
    db.query(SessionTraining).filter(SessionTraining.session_id.in_(session_ids)).delete(synchronize_session=False)
    db.query(ClinicalSession).filter(ClinicalSession.patient_id == patient.id).delete(synchronize_session=False)
    db.query(PatientAssignment).filter(PatientAssignment.patient_id == patient.id).delete(synchronize_session=False)

    plan = db.query(TreatmentPlan).filter(TreatmentPlan.patient_id == patient.id).first()
    if plan is not None:
        objective_ids_subquery = db.query(Objective.id).filter(Objective.plan_id == plan.id).subquery()
        db.query(ObjectiveComment).filter(ObjectiveComment.objective_id.in_(objective_ids_subquery.select())).delete(
            synchronize_session=False
        )
        db.query(ObjectiveTraining).filter(ObjectiveTraining.objective_id.in_(objective_ids_subquery.select())).delete(
            synchronize_session=False
        )
        db.query(Objective).filter(Objective.plan_id == plan.id).delete(synchronize_session=False)
        db.delete(plan)

    db.query(ReportSummary).filter(ReportSummary.patient_id == patient.id).delete(synchronize_session=False)

    db.add(
        AuditLog(
            actor_user_id=None,
            action="patient_permanently_purged",
            entity_type="patient",
            entity_id=patient.id,
            before={"deleted_at": patient.deleted_at.isoformat()},
            after=None,
        )
    )
    db.delete(patient)


def _purge_standalone_objective(db, objective: Objective) -> None:
    """Objetivos excluídos independentemente do paciente (Seção 13.3)."""
    db.query(ObjectiveComment).filter(ObjectiveComment.objective_id == objective.id).delete(synchronize_session=False)
    db.query(ObjectiveTraining).filter(ObjectiveTraining.objective_id == objective.id).delete(synchronize_session=False)
    db.add(
        AuditLog(
            actor_user_id=None,
            action="objective_permanently_purged",
            entity_type="objective",
            entity_id=objective.id,
            before={"deleted_at": objective.deleted_at.isoformat()},
            after=None,
        )
    )
    db.delete(objective)


def _purge_resource(db, resource: Resource) -> None:
    """Seção 15/16 — remove o objeto do storage S3-compatível e o registro do banco."""
    try:
        file_service.delete_object(resource.file_key)
    except Exception:
        pass  # o registro ainda é purgado do banco mesmo se o storage já não tiver o objeto
    db.add(
        AuditLog(
            actor_user_id=None,
            action="resource_permanently_purged",
            entity_type="resource",
            entity_id=resource.id,
            before={"deleted_at": resource.deleted_at.isoformat()},
            after=None,
        )
    )
    db.delete(resource)


@celery_app.task(name="app.tasks.purge.purge_expired_soft_deleted_records")
def purge_expired_soft_deleted_records() -> int:
    """Seção 16.2 — executa diariamente e remove definitivamente registros com
    soft delete há mais de 60 dias (pacientes e seus dados relacionados,
    objetivos excluídos isoladamente, e recursos terapêuticos)."""
    db = SessionLocal()
    purged_count = 0
    try:
        cutoff = _cutoff()

        expired_patients = (
            db.query(Patient).filter(Patient.deleted_at.isnot(None), Patient.deleted_at < cutoff).all()
        )
        for patient in expired_patients:
            _purge_patient(db, patient)
            db.commit()
            purged_count += 1

        expired_objectives = (
            db.query(Objective).filter(Objective.deleted_at.isnot(None), Objective.deleted_at < cutoff).all()
        )
        for objective in expired_objectives:
            _purge_standalone_objective(db, objective)
            db.commit()
            purged_count += 1

        expired_resources = (
            db.query(Resource).filter(Resource.deleted_at.isnot(None), Resource.deleted_at < cutoff).all()
        )
        for resource in expired_resources:
            _purge_resource(db, resource)
            db.commit()
            purged_count += 1
    finally:
        db.close()

    return purged_count
