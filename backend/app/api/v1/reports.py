import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.professional_performance import ProfessionalPerformanceResponse
from app.schemas.report import (
    ReportDataResponse,
    ReportSummaryGenerateRequest,
    ReportSummaryResponse,
    ReportSummaryUpdateRequest,
)
from app.services import (
    patient_service,
    professional_performance_service,
    report_export_service,
    report_service,
    report_summary_service,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/patients/{patient_id}", response_model=ReportDataResponse)
def get_report(
    patient_id: uuid.UUID,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    training_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    professional_id: uuid.UUID | None = None,
    compare_from: datetime.date | None = None,
    compare_to: datetime.date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 14.1/14.2/14.3 — dados agregados a partir das tentativas registradas."""
    patient_service.assert_full_clinical_access(user)
    return report_service.get_report_data(
        db,
        user,
        patient_id,
        date_from=date_from,
        date_to=date_to,
        training_id=training_id,
        category_id=category_id,
        professional_id=professional_id,
        compare_from=compare_from,
        compare_to=compare_to,
    )


@router.get("/patients/{patient_id}/summary", response_model=ReportSummaryResponse)
def get_summary(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    summary = report_summary_service.get_latest_summary(db, user, patient_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No summary generated yet")
    return summary


@router.post(
    "/patients/{patient_id}/summary/generate",
    response_model=ReportSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_summary(
    patient_id: uuid.UUID,
    payload: ReportSummaryGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 14.5 — gera um rascunho objetivo com base nos dados selecionados
    (regra determinística nesta fase; ver README sobre o provedor de IA)."""
    return report_summary_service.generate_summary(
        db,
        user,
        patient_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        training_id=payload.training_id,
        category_id=payload.category_id,
        professional_id=payload.professional_id,
    )


@router.patch("/summaries/{summary_id}", response_model=ReportSummaryResponse)
def update_summary(
    summary_id: uuid.UUID,
    payload: ReportSummaryUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 14.5 — o terapeuta pode editar, aprovar ou descartar o texto."""
    return report_summary_service.update_summary(
        db, user, summary_id, content=payload.content, new_status=payload.status
    )


@router.get("/patients/{patient_id}/export.csv")
def export_csv(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Seção 14.6 — exportar dados tabulares em CSV (compatível com Excel)."""
    content = report_export_service.export_csv(db, user, patient_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report-{patient_id}.csv"'},
    )


@router.get("/patients/{patient_id}/export.pdf")
def export_pdf(
    patient_id: uuid.UUID,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seção 14.6 — exportar relatório consolidado em PDF."""
    summary = report_summary_service.get_latest_summary(db, user, patient_id)
    content = report_export_service.export_pdf(
        db,
        user,
        patient_id,
        date_from=date_from,
        date_to=date_to,
        summary_text=summary.content if summary else None,
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{patient_id}.pdf"'},
    )


@router.get("/professionals/{professional_id}/performance", response_model=ProfessionalPerformanceResponse)
def get_professional_performance(
    professional_id: uuid.UUID,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Addendum v3.0, RF-31 — relatório de desempenho do profissional/AT."""
    return professional_performance_service.get_professional_performance(
        db, user, professional_id, date_from=date_from, date_to=date_to
    )


@router.get("/professionals/{professional_id}/performance/export.pdf")
def export_professional_performance_pdf(
    professional_id: uuid.UUID,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = report_export_service.export_professional_performance_pdf(
        db, user, professional_id, date_from=date_from, date_to=date_to
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="desempenho-{professional_id}.pdf"'},
    )
