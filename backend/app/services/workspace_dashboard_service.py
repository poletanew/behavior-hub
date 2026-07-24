import collections
import datetime
import uuid

from sqlalchemy.orm import Session as DbSession

from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.training import Training, TrainingCategory
from app.models.user import User
from app.services.calculations import accuracy_pct

WEEKLY_CHART_MAX_POINTS = 12
TRAINING_RANKING_MAX_POINTS = 20


def _tenant_scope_filter(user: User):
    if user.clinic_id is not None:
        return ClinicalSession.clinic_id == user.clinic_id
    return ClinicalSession.individual_owner_id == user.id


def _week_label(day: datetime.date) -> str:
    iso_year, iso_week, _ = day.isocalendar()
    return f"Sem {iso_week}"


def get_workspace_dashboard(
    db: DbSession,
    user: User,
    *,
    patient_id: uuid.UUID | None,
    professional_id: uuid.UUID | None,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
) -> dict:
    """Área de Trabalho — indicadores e gráficos calculados em tempo real a partir
    dos atendimentos e tentativas já registrados (nunca dados fixos)."""
    session_query = db.query(ClinicalSession).filter(
        _tenant_scope_filter(user), ClinicalSession.deleted_at.is_(None)
    )
    if patient_id is not None:
        session_query = session_query.filter(ClinicalSession.patient_id == patient_id)
    if professional_id is not None:
        session_query = session_query.filter(ClinicalSession.professional_id == professional_id)
    if date_from is not None:
        session_query = session_query.filter(ClinicalSession.occurred_at >= date_from)
    if date_to is not None:
        session_query = session_query.filter(
            ClinicalSession.occurred_at <= datetime.datetime.combine(date_to, datetime.time.max)
        )
    sessions = session_query.all()
    session_ids = [s.id for s in sessions]

    if not session_ids:
        return {
            "kpis": {"sessions_count": 0, "programs_count": 0, "avg_trials_per_session": 0.0, "avg_accuracy_pct": 0.0},
            "area_performance": [],
            "training_ranking": [],
            "distribution": {"correct": 0, "incorrect": 0, "partial": 0, "no_response": 0},
            "weekly_sessions": [],
        }

    rows = (
        db.query(
            Trial,
            SessionTraining.session_id,
            Training.id,
            Training.title,
            TrainingCategory.name,
        )
        .join(SessionTraining, Trial.session_training_id == SessionTraining.id)
        .join(Training, SessionTraining.training_id == Training.id)
        .join(TrainingCategory, Training.category_id == TrainingCategory.id)
        .filter(SessionTraining.session_id.in_(session_ids), Trial.deleted_at.is_(None))
        .all()
    )

    trials_by_session: dict[uuid.UUID, list[Trial]] = collections.defaultdict(list)
    trials_by_session_training: dict[tuple[uuid.UUID, uuid.UUID], list[Trial]] = collections.defaultdict(list)
    category_by_session_training: dict[tuple[uuid.UUID, uuid.UUID], str] = {}
    trials_by_training: dict[uuid.UUID, dict] = {}
    programs_in_scope: set[uuid.UUID] = set()
    result_counts = {"correct": 0, "incorrect": 0, "partial": 0, "no_response": 0}

    for trial, session_id, training_id, training_title, category_name in rows:
        trials_by_session[session_id].append(trial)
        trials_by_session_training[(session_id, training_id)].append(trial)
        category_by_session_training[(session_id, training_id)] = category_name
        trials_by_training.setdefault(training_id, {"title": training_title, "trials": []})
        trials_by_training[training_id]["trials"].append(trial)
        programs_in_scope.add(training_id)
        result_counts[trial.result.value] += 1

    area_accuracy_samples: dict[str, list[float]] = collections.defaultdict(list)
    for key, trials in trials_by_session_training.items():
        acc = accuracy_pct(trials)
        if acc is not None:
            area_accuracy_samples[category_by_session_training[key]].append(acc)

    sessions_count = len(sessions)
    programs_count = len(programs_in_scope)
    total_trials = sum(len(trials) for trials in trials_by_session.values())
    avg_trials_per_session = round(total_trials / sessions_count, 1) if sessions_count else 0.0

    per_session_accuracies = [accuracy_pct(trials) for trials in trials_by_session.values()]
    per_session_accuracies = [a for a in per_session_accuracies if a is not None]
    avg_accuracy_pct = round(sum(per_session_accuracies) / len(per_session_accuracies), 0) if per_session_accuracies else 0.0

    area_performance = [
        {"area": area, "accuracy_pct": round(sum(samples) / len(samples), 0)}
        for area, samples in area_accuracy_samples.items()
    ]

    training_ranking = []
    for training_id, data in trials_by_training.items():
        acc = accuracy_pct(data["trials"])
        if acc is not None:
            training_ranking.append({"training_id": training_id, "title": data["title"], "accuracy_pct": acc})
    training_ranking.sort(key=lambda t: t["accuracy_pct"], reverse=True)
    training_ranking = training_ranking[:TRAINING_RANKING_MAX_POINTS]

    weekly_counts: dict[str, int] = collections.defaultdict(int)
    for session in sessions:
        weekly_counts[_week_label(session.occurred_at.date())] += 1
    weekly_sessions = [{"week_label": w, "sessions_count": c} for w, c in sorted(weekly_counts.items())]
    weekly_sessions = weekly_sessions[-WEEKLY_CHART_MAX_POINTS:]

    return {
        "kpis": {
            "sessions_count": sessions_count,
            "programs_count": programs_count,
            "avg_trials_per_session": avg_trials_per_session,
            "avg_accuracy_pct": avg_accuracy_pct,
        },
        "area_performance": area_performance,
        "training_ranking": training_ranking,
        "distribution": result_counts,
        "weekly_sessions": weekly_sessions,
    }
