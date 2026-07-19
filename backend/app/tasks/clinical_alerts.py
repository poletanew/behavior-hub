from app.db.session import SessionLocal
from app.models.patient import Patient
from app.services import clinical_alert_service, clinical_suggestion_service
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.clinical_alerts.recompute_clinical_alerts_daily")
def recompute_clinical_alerts_daily() -> int:
    """Seção 29.1/29.9 — varredura diária necessária especificamente para o
    alerta de "sem coleta": ao contrário de regressão/estagnação/fading (que
    são recalculados a cada nova tentativa salva), a ausência de coleta só se
    torna verdadeira com a passagem do tempo, sem nenhum evento de tentativa
    para disparar o recálculo. Também recalcula as sugestões clínicas da Fase
    4b (mesma varredura, já que "novos programas" pode mudar sem uma nova
    tentativa — por exemplo, quando um objetivo é descontinuado)."""
    db = SessionLocal()
    triggered_count = 0
    try:
        patients = db.query(Patient).filter(Patient.deleted_at.is_(None)).all()
        for patient in patients:
            new_alerts = clinical_alert_service.recompute_alerts_for_patient(db, patient)
            triggered_count += len(new_alerts)
            new_suggestions = clinical_suggestion_service.recompute_suggestions_for_patient(db, patient)
            triggered_count += len(new_suggestions)
    finally:
        db.close()

    return triggered_count
