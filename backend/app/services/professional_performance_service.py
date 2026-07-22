import datetime
import statistics
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import UserType
from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.user import User
from app.services.calculations import accuracy_pct

# Addendum v3.0, RF-31 — "eficiência do aplicador" não tem uma definição
# numérica no addendum; usamos o desvio-padrão do percentual de acerto entre
# sessões (menor variação = procedimento aplicado de forma mais consistente)
# e traduzimos em uma faixa de 3 níveis, mesmo estilo de limiar fixo já usado
# em LOW_ADHERENCE_THRESHOLD_PCT (supervisor_dashboard_service).
HIGH_EFFICIENCY_MAX_VARIABILITY_PP = 10
MEDIUM_EFFICIENCY_MAX_VARIABILITY_PP = 20


def _require_team_view(user: User) -> None:
    if user.clinic_id is None or user.user_type not in (UserType.CLINIC_ADMIN, UserType.SUPERVISOR):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def _get_subject_or_404(db: Session, user: User, professional_id: uuid.UUID) -> User:
    subject = db.get(User, professional_id)
    if subject is None or subject.clinic_id != user.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found")
    return subject


def _efficiency_label(variability_pp: float | None) -> str | None:
    if variability_pp is None:
        return None
    if variability_pp <= HIGH_EFFICIENCY_MAX_VARIABILITY_PP:
        return "alta"
    if variability_pp <= MEDIUM_EFFICIENCY_MAX_VARIABILITY_PP:
        return "media"
    return "baixa"


def get_professional_performance(
    db: Session,
    user: User,
    professional_id: uuid.UUID,
    *,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> dict:
    """Addendum v3.0, RF-31 — relatório individual por profissional/AT,
    distinto do Painel de Supervisão (Seção 29.4, que é uma visão consolidada
    de toda a equipe de uma vez): sessões realizadas, consistência de
    registro (sessões com ao menos uma tentativa registrada, não só
    "abertas"), percentual médio de acerto e "eficiência do aplicador"."""
    _require_team_view(user)
    subject = _get_subject_or_404(db, user, professional_id)

    query = db.query(ClinicalSession).filter(
        ClinicalSession.professional_id == subject.id, ClinicalSession.deleted_at.is_(None)
    )
    if date_from is not None:
        query = query.filter(ClinicalSession.occurred_at >= date_from)
    if date_to is not None:
        query = query.filter(ClinicalSession.occurred_at <= datetime.datetime.combine(date_to, datetime.time.max))
    sessions = query.all()
    session_ids = [s.id for s in sessions]
    sessions_count = len(sessions)

    trials_by_session: dict[uuid.UUID, list[Trial]] = {}
    if session_ids:
        rows = (
            db.query(SessionTraining.session_id, Trial)
            .join(Trial, Trial.session_training_id == SessionTraining.id)
            .filter(SessionTraining.session_id.in_(session_ids), Trial.deleted_at.is_(None))
            .all()
        )
        for session_id, trial in rows:
            trials_by_session.setdefault(session_id, []).append(trial)

    registration_consistency_pct = (
        round(len(trials_by_session) / sessions_count * 100, 1) if sessions_count else None
    )

    all_trials = [trial for trials in trials_by_session.values() for trial in trials]
    average_accuracy_pct = accuracy_pct(all_trials)

    per_session_accuracy = [
        pct for trials in trials_by_session.values() if (pct := accuracy_pct(trials)) is not None
    ]
    procedure_variability_pp = (
        round(statistics.pstdev(per_session_accuracy), 1) if len(per_session_accuracy) >= 2 else None
    )

    return {
        "professional_id": subject.id,
        "professional_name": subject.name,
        "professional_role": subject.user_type.value,
        "sessions_count": sessions_count,
        "registration_consistency_pct": registration_consistency_pct,
        "average_accuracy_pct": average_accuracy_pct,
        "procedure_variability_pp": procedure_variability_pp,
        "applier_efficiency_label": _efficiency_label(procedure_variability_pp),
    }
