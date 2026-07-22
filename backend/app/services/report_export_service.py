import csv
import datetime
import io
import uuid

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy.orm import Session

from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.training import Training, TrainingCategory
from app.models.user import User
from app.services import patient_service, professional_performance_service, report_service, white_label_service

EFFICIENCY_LABEL_PT = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}


def _fetch_export_rows(db, patient_id, **filters):
    return (
        db.query(
            ClinicalSession.occurred_at,
            Training.title,
            TrainingCategory.name,
            Trial.attempt_number,
            Trial.result,
            Trial.prompt_level,
            Trial.notes,
        )
        .join(SessionTraining, Trial.session_training_id == SessionTraining.id)
        .join(ClinicalSession, SessionTraining.session_id == ClinicalSession.id)
        .join(Training, SessionTraining.training_id == Training.id)
        .join(TrainingCategory, Training.category_id == TrainingCategory.id)
        .filter(
            ClinicalSession.patient_id == patient_id,
            ClinicalSession.deleted_at.is_(None),
            Trial.deleted_at.is_(None),
        )
        .order_by(ClinicalSession.occurred_at, Training.title, Trial.attempt_number)
        .all()
    )


def export_csv(
    db: Session,
    user: User,
    patient_id: uuid.UUID,
) -> str:
    """Seção 14.6 — exportar dados tabulares em Excel/CSV."""
    patient_service.get_patient_or_404(db, user, patient_id)
    rows = _fetch_export_rows(db, patient_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Data", "Treino", "Categoria", "Tentativa", "Resultado", "Nível de ajuda", "Observação"])
    for occurred_at, training_title, category_name, attempt_number, result, prompt_level, notes in rows:
        writer.writerow(
            [
                occurred_at.strftime("%Y-%m-%d %H:%M"),
                training_title,
                category_name,
                attempt_number,
                result.value,
                prompt_level.value,
                notes or "",
            ]
        )
    return buffer.getvalue()


def export_pdf(
    db: Session,
    user: User,
    patient_id: uuid.UUID,
    *,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    summary_text: str | None,
) -> bytes:
    """Seção 14.6 — relatório consolidado em PDF, com identificação, filtros
    aplicados e data de geração. Seção 32.9 — clínicas Enterprise podem trocar
    o nome exibido e a cor de destaque; o logo em si não é embutido no PDF
    (evitaria o backend precisar buscar uma URL externa arbitrária no
    momento da exportação — risco de SSRF sem benefício real, já que o nome/
    cor já cobrem a necessidade de identidade visual em texto). O rodapé
    "Powered by Behavior Hub" nunca é removido, mesmo com white-label ativo."""
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    data = report_service.get_report_data(db, user, patient_id, date_from=date_from, date_to=date_to)
    branding = white_label_service.get_branding_for_clinic(db, patient.clinic_id)
    accent_color = branding["brand_color"] if branding["enabled"] and branding["brand_color"] else "#1D4ED8"
    title = branding["display_name"] if branding["enabled"] and branding["display_name"] else "Behavior Hub"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"{title} — Relatório Consolidado", styles["Title"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"Paciente: {patient.name}", styles["Normal"]))
    period_label = (
        f"{date_from.strftime('%d/%m/%Y')} a {date_to.strftime('%d/%m/%Y')}" if date_from and date_to else "Todo o histórico"
    )
    elements.append(Paragraph(f"Período: {period_label}", styles["Normal"]))
    elements.append(
        Paragraph(
            f"Gerado em: {datetime.datetime.now(datetime.timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    if summary_text:
        elements.append(Paragraph("Resumo", styles["Heading2"]))
        elements.append(Paragraph(summary_text, styles["Normal"]))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("Percentual de acerto por treino", styles["Heading2"]))
    table_data = [["Treino", "Percentual de acerto", "Tentativas"]]
    for row in data["bar"]:
        table_data.append(
            [row["training_title"], f"{row['accuracy_pct']}%" if row["accuracy_pct"] is not None else "-", row["sample_size"]]
        )
    table = Table(table_data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(accent_color)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Powered by Behavior Hub", styles["Normal"]))

    doc.build(elements)
    return buffer.getvalue()


def export_professional_performance_pdf(
    db: Session,
    user: User,
    professional_id: uuid.UUID,
    *,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
) -> bytes:
    """Addendum v3.0, RF-31 — relatório de desempenho do profissional/AT
    exportável em PDF, mesmo padrão visual do export_pdf de paciente."""
    data = professional_performance_service.get_professional_performance(
        db, user, professional_id, date_from=date_from, date_to=date_to
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Behavior Hub — Desempenho do Profissional/AT", styles["Title"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"Profissional: {data['professional_name']}", styles["Normal"]))
    period_label = (
        f"{date_from.strftime('%d/%m/%Y')} a {date_to.strftime('%d/%m/%Y')}" if date_from and date_to else "Todo o histórico"
    )
    elements.append(Paragraph(f"Período: {period_label}", styles["Normal"]))
    elements.append(
        Paragraph(
            f"Gerado em: {datetime.datetime.now(datetime.timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    efficiency_label = data["applier_efficiency_label"]
    table_data = [
        ["Indicador", "Valor"],
        ["Atendimentos realizados", data["sessions_count"]],
        [
            "Consistência de registro",
            f"{data['registration_consistency_pct']}%" if data["registration_consistency_pct"] is not None else "-",
        ],
        [
            "Percentual médio de acerto",
            f"{data['average_accuracy_pct']}%" if data["average_accuracy_pct"] is not None else "-",
        ],
        [
            "Variabilidade de procedimento entre sessões",
            f"{data['procedure_variability_pp']} p.p." if data["procedure_variability_pp"] is not None else "-",
        ],
        ["Eficiência do aplicador", EFFICIENCY_LABEL_PT.get(efficiency_label, "-") if efficiency_label else "-"],
    ]
    table = Table(table_data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Powered by Behavior Hub", styles["Normal"]))

    doc.build(elements)
    return buffer.getvalue()
