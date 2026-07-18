import datetime

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.patient import Patient, PatientAssignment
from app.models.session import ClinicalSession, SessionTraining, Trial
from app.tasks.celery_app import celery_app

settings = get_settings()


@celery_app.task(name="app.tasks.purge.purge_expired_soft_deleted_records")
def purge_expired_soft_deleted_records() -> int:
    """Seção 16.2 — remove definitivamente registros com soft delete ha mais de 60 dias.
    Respeita a ordem de dependencias (trials -> session_trainings -> sessions ->
    assignments -> patient) dentro de uma transacao por paciente (Seção 16.3)."""
    db = SessionLocal()
    purged_count = 0
    try:
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=settings.DELETED_DATA_RETENTION_DAYS
        )
        expired_patients = (
            db.query(Patient)
            .filter(Patient.deleted_at.isnot(None), Patient.deleted_at < cutoff)
            .all()
        )

        for patient in expired_patients:
            session_ids = [
                row[0] for row in db.query(ClinicalSession.id).filter(ClinicalSession.patient_id == patient.id).all()
            ]
            session_training_ids_subquery = (
                db.query(SessionTraining.id).filter(SessionTraining.session_id.in_(session_ids)).subquery()
            )
            db.query(Trial).filter(Trial.session_training_id.in_(session_training_ids_subquery.select())).delete(
                synchronize_session=False
            )
            db.query(SessionTraining).filter(SessionTraining.session_id.in_(session_ids)).delete(
                synchronize_session=False
            )
            db.query(ClinicalSession).filter(ClinicalSession.patient_id == patient.id).delete(
                synchronize_session=False
            )
            db.query(PatientAssignment).filter(PatientAssignment.patient_id == patient.id).delete(
                synchronize_session=False
            )

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
            db.commit()
            purged_count += 1
    finally:
        db.close()

    return purged_count
