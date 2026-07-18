import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import ReportSummaryStatus
from app.models.report_summary import ReportSummary
from app.models.user import User
from app.services import audit_service, patient_service, report_service


def _draft_text(period_start: datetime.date, period_end: datetime.date, data: dict) -> str:
    """Seção 14.5 — resumo objetivo, rascunho editável. Gerado por regra determinística
    nesta fase (sem chamada a API de IA externa — ver Seção 28.6/README); nunca emite
    diagnóstico ou causalidade."""
    total = data["total_trials"]
    if total == 0:
        return (
            f"Não há tentativas registradas entre {period_start.strftime('%d/%m/%Y')} e "
            f"{period_end.strftime('%d/%m/%Y')} para os filtros selecionados."
        )

    all_trials_flat = data["pie"]
    correct = all_trials_flat["correct"]
    incorrect = all_trials_flat["incorrect"]
    partial = all_trials_flat["partial"]
    no_response = all_trials_flat["no_response"]

    avg_accuracy = round(correct / total * 100, 1) if total else None
    n_trainings = len(data["bar"])

    return (
        f"Resumo do período de {period_start.strftime('%d/%m/%Y')} a {period_end.strftime('%d/%m/%Y')}: "
        f"foram registradas {total} tentativa(s) em {n_trainings} treino(s). "
        f"Percentual de acerto no período: {avg_accuracy}%. "
        f"Distribuição de resultados — corretas: {correct}, incorretas: {incorrect}, parciais: {partial}, "
        f"não respondidas: {no_response}. "
        "Este é um resumo objetivo calculado a partir dos dados coletados — não constitui diagnóstico, "
        "não afirma causalidade e deve ser revisado pelo profissional responsável antes de aprovar ou exportar."
    )


def generate_summary(
    db: Session,
    user: User,
    patient_id: uuid.UUID,
    *,
    period_start: datetime.date,
    period_end: datetime.date,
    training_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    professional_id: uuid.UUID | None,
) -> ReportSummary:
    patient_service.get_patient_or_404(db, user, patient_id)

    data = report_service.get_report_data(
        db,
        user,
        patient_id,
        date_from=period_start,
        date_to=period_end,
        training_id=training_id,
        category_id=category_id,
        professional_id=professional_id,
    )
    content = _draft_text(period_start, period_end, data)

    previous = (
        db.query(ReportSummary)
        .filter(ReportSummary.patient_id == patient_id)
        .order_by(ReportSummary.version.desc())
        .first()
    )
    next_version = (previous.version + 1) if previous else 1

    summary = ReportSummary(
        patient_id=patient_id,
        period_start=period_start,
        period_end=period_end,
        version=next_version,
        content=content,
        status=ReportSummaryStatus.DRAFT,
        generated_by="rule_based_draft",
        data_snapshot={
            "total_trials": data["total_trials"],
            "pie": data["pie"],
            "bar": [
                {**row, "training_id": str(row["training_id"])}
                for row in data["bar"]
            ],
            "filters": {
                "training_id": str(training_id) if training_id else None,
                "category_id": str(category_id) if category_id else None,
                "professional_id": str(professional_id) if professional_id else None,
            },
        },
        author_id=user.id,
    )
    db.add(summary)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="report_summary_generated",
        entity_type="report_summary",
        entity_id=None,
        after={"patient_id": str(patient_id), "version": next_version},
    )
    db.commit()
    db.refresh(summary)
    return summary


def get_latest_summary(db: Session, user: User, patient_id: uuid.UUID) -> ReportSummary | None:
    patient_service.get_patient_or_404(db, user, patient_id)
    return (
        db.query(ReportSummary)
        .filter(ReportSummary.patient_id == patient_id)
        .order_by(ReportSummary.version.desc())
        .first()
    )


def update_summary(
    db: Session, user: User, summary_id: uuid.UUID, *, content: str | None, new_status: str | None
) -> ReportSummary:
    """Seção 14.5 — permitir que o terapeuta edite, aprove ou descarte o texto."""
    summary = db.get(ReportSummary, summary_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report summary not found")
    patient_service.get_patient_or_404(db, user, summary.patient_id)

    before = {"content": summary.content, "status": summary.status.value}
    if content is not None:
        summary.content = content
    if new_status is not None:
        summary.status = ReportSummaryStatus(new_status)

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="report_summary_updated",
        entity_type="report_summary",
        entity_id=summary.id,
        before=before,
        after={"content": summary.content, "status": summary.status.value},
    )
    db.commit()
    db.refresh(summary)
    return summary
