import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.enums import AssessmentProtocol, UserType
from app.models.patient import Patient
from app.models.user import User
from app.schemas.assessment import AssessmentCreateRequest, AssessmentUpdateRequest
from app.services import assessment_protocols, audit_service, patient_service
from app.services.rbac_service import can_restore_deleted_data


def _domain_lookup(protocol: AssessmentProtocol) -> dict[str, dict]:
    definition = assessment_protocols.get_protocol_definition(protocol)
    return {domain["domain_code"]: domain for domain in definition["domains"]}


def _build_raw_scores(protocol: AssessmentProtocol, domain_scores: list) -> list[dict]:
    lookup = _domain_lookup(protocol)
    rows = []
    for entry in domain_scores:
        domain = lookup.get(entry.domain_code)
        if domain is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown domain_code '{entry.domain_code}' for {protocol.value}"
            )
        max_value = entry.max_value if entry.max_value is not None else domain["max_value"]
        if max_value is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"max_value is required for domain '{entry.domain_code}' ({protocol.value} has no default)",
            )
        if entry.raw_value > max_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"raw_value cannot exceed max_value for domain '{entry.domain_code}'",
            )
        rows.append(
            {
                "domain_code": entry.domain_code,
                "domain_label": domain["domain_label"],
                "raw_value": entry.raw_value,
                "max_value": max_value,
                "normalized_pct": round(entry.raw_value / max_value * 100, 1),
            }
        )
    return rows


def create_assessment(db: Session, user: User, patient_id: uuid.UUID, payload: AssessmentCreateRequest) -> Assessment:
    """Seção 27.2/30.1 — registra uma aplicação de protocolo padronizado.
    Um par (paciente, protocolo, data) nunca se repete (Seção 27.3 — evita
    duplicidade de aplicação no mesmo dia)."""
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    raw_scores = _build_raw_scores(payload.protocol, payload.domain_scores)

    existing = (
        db.query(Assessment)
        .filter(
            Assessment.patient_id == patient.id,
            Assessment.protocol == payload.protocol,
            Assessment.applied_date == payload.applied_date,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An assessment for this protocol and date already exists for this patient",
        )

    assessment = Assessment(
        clinic_id=patient.clinic_id,
        individual_owner_id=patient.individual_owner_id,
        patient_id=patient.id,
        professional_id=user.id,
        protocol=payload.protocol,
        applied_date=payload.applied_date,
        raw_scores=raw_scores,
        summary=payload.summary,
    )
    db.add(assessment)
    db.flush()

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="assessment_created",
        entity_type="assessment",
        entity_id=assessment.id,
        after={"protocol": assessment.protocol.value, "applied_date": assessment.applied_date.isoformat()},
    )
    db.commit()
    db.refresh(assessment)
    return assessment


def list_assessments(db: Session, user: User, patient_id: uuid.UUID, protocol: AssessmentProtocol | None = None) -> list[Assessment]:
    patient_service.get_patient_or_404(db, user, patient_id)
    query = db.query(Assessment).filter(Assessment.patient_id == patient_id, Assessment.deleted_at.is_(None))
    if protocol is not None:
        query = query.filter(Assessment.protocol == protocol)
    return query.order_by(Assessment.applied_date).all()


def _get_assessment_or_404(db: Session, user: User, assessment_id: uuid.UUID, *, include_deleted: bool = False) -> tuple[Patient, Assessment]:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None or (not include_deleted and assessment.deleted_at is not None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    patient = patient_service.get_patient_or_404(db, user, assessment.patient_id)
    return patient, assessment


def get_assessment(db: Session, user: User, assessment_id: uuid.UUID) -> Assessment:
    _patient, assessment = _get_assessment_or_404(db, user, assessment_id)
    return assessment


def update_assessment(db: Session, user: User, assessment_id: uuid.UUID, payload: AssessmentUpdateRequest) -> Assessment:
    """Seção 30.3 — a interpretação clínica permanece com o profissional; o
    sistema só apoia o registro (aqui, editar o texto de resumo)."""
    _patient, assessment = _get_assessment_or_404(db, user, assessment_id)
    before = {"summary": assessment.summary}
    if payload.summary is not None:
        assessment.summary = payload.summary

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="assessment_updated",
        entity_type="assessment",
        entity_id=assessment.id,
        before=before,
        after={"summary": assessment.summary},
    )
    db.commit()
    db.refresh(assessment)
    return assessment


def soft_delete_assessment(db: Session, user: User, assessment_id: uuid.UUID) -> None:
    _patient, assessment = _get_assessment_or_404(db, user, assessment_id)
    assessment.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    assessment.deleted_by = user.id
    audit_service.record(
        db, actor_user_id=user.id, action="assessment_deleted", entity_type="assessment", entity_id=assessment.id
    )
    db.commit()


def restore_assessment(db: Session, user: User, assessment_id: uuid.UUID) -> Assessment:
    _patient, assessment = _get_assessment_or_404(db, user, assessment_id, include_deleted=True)
    if assessment.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment is not deleted")
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL) and not can_restore_deleted_data(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to restore assessments")

    assessment.deleted_at = None
    assessment.deleted_by = None
    audit_service.record(
        db, actor_user_id=user.id, action="assessment_restored", entity_type="assessment", entity_id=assessment.id
    )
    db.commit()
    db.refresh(assessment)
    return assessment


def list_deleted_assessments(db: Session, user: User) -> list[Assessment]:
    tenant_filter = (Assessment.clinic_id == user.clinic_id) if user.clinic_id else (Assessment.individual_owner_id == user.id)
    return db.query(Assessment).filter(Assessment.deleted_at.isnot(None), tenant_filter).all()


def _interpretive_summary(domains: list[dict], earliest_date: datetime.date, latest_date: datetime.date) -> str:
    """Seção 30.2 — "texto interpretativo... editável, descrevendo a evolução
    observada — nunca diagnóstico". Rascunho determinístico (mesmo padrão do
    resumo de Reports — Seção 14.5); ver README sobre o provedor de IA."""
    if not domains:
        return (
            "Não há domínios em comum entre as avaliações selecionadas para comparar — não constitui "
            "diagnóstico. Revise antes de aprovar ou exportar."
        )

    improved = [d for d in domains if d["gain_absolute_pp"] > 0]
    declined = [d for d in domains if d["gain_absolute_pp"] < 0]
    stable = [d for d in domains if d["gain_absolute_pp"] == 0]

    parts = [
        f"Comparação entre {earliest_date.strftime('%d/%m/%Y')} e {latest_date.strftime('%d/%m/%Y')} "
        f"em {len(domains)} domínio(s) em comum."
    ]
    if improved:
        parts.append(
            f"{len(improved)} domínio(s) com ganho percentual positivo (maior: "
            f"{max(improved, key=lambda d: d['gain_absolute_pp'])['domain_label']}, "
            f"+{max(d['gain_absolute_pp'] for d in improved)} p.p.)."
        )
    if declined:
        parts.append(f"{len(declined)} domínio(s) com queda percentual.")
    if stable:
        parts.append(f"{len(stable)} domínio(s) sem variação.")
    parts.append(
        "Este é um resumo objetivo calculado a partir dos dados registrados — não constitui diagnóstico, "
        "não afirma causalidade e deve ser revisado pelo profissional responsável antes de aprovar ou exportar."
    )
    return " ".join(parts)


def compare_assessments(db: Session, user: User, patient_id: uuid.UUID, protocol: AssessmentProtocol, assessment_ids: list[uuid.UUID]) -> dict:
    """Seção 30.2/AC-19 — ganho absoluto e percentual por domínio entre a
    aplicação mais antiga e a mais recente do conjunto selecionado, usando
    normalized_pct (não raw_value, já que max_value pode variar entre
    aplicações — Seção 30.1.1)."""
    patient_service.get_patient_or_404(db, user, patient_id)
    if len(assessment_ids) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least two assessments are required to compare")

    assessments = (
        db.query(Assessment)
        .filter(
            Assessment.id.in_(assessment_ids),
            Assessment.patient_id == patient_id,
            Assessment.protocol == protocol,
            Assessment.deleted_at.is_(None),
        )
        .order_by(Assessment.applied_date)
        .all()
    )
    if len(assessments) != len(set(assessment_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more assessments not found for this patient/protocol")

    earliest, latest = assessments[0], assessments[-1]
    earliest_by_domain = {row["domain_code"]: row for row in earliest.raw_scores}
    latest_by_domain = {row["domain_code"]: row for row in latest.raw_scores}
    common_codes = [code for code in earliest_by_domain if code in latest_by_domain]

    domains = []
    for code in common_codes:
        earliest_pct = earliest_by_domain[code]["normalized_pct"]
        latest_pct = latest_by_domain[code]["normalized_pct"]
        gain_absolute = round(latest_pct - earliest_pct, 1)
        gain_relative = round(gain_absolute / earliest_pct * 100, 1) if earliest_pct else None
        domains.append(
            {
                "domain_code": code,
                "domain_label": latest_by_domain[code]["domain_label"],
                "earliest_pct": earliest_pct,
                "latest_pct": latest_pct,
                "gain_absolute_pp": gain_absolute,
                "gain_relative_pct": gain_relative,
            }
        )

    return {
        "protocol": protocol,
        "assessment_ids": [a.id for a in assessments],
        "applied_dates": [a.applied_date for a in assessments],
        "domains": domains,
        "interpretive_summary": _interpretive_summary(domains, earliest.applied_date, latest.applied_date),
    }
