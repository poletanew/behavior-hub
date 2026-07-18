import collections
import datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import TrialResult
from app.models.session import ClinicalSession, SessionTraining, Trial
from app.models.training import Training, TrainingCategory
from app.models.user import User
from app.services import patient_service
from app.services.calculations import accuracy_pct, independence_pct, prompt_level_distribution

RADAR_MIN_SAMPLE_SIZE = 5


class _TrialRow:
    __slots__ = ("trial", "session_id", "session_date", "training_id", "training_title", "category_name")

    def __init__(self, trial, session_id, session_date, training_id, training_title, category_name):
        self.trial = trial
        self.session_id = session_id
        self.session_date = session_date
        self.training_id = training_id
        self.training_title = training_title
        self.category_name = category_name


def _fetch_rows(
    db: Session,
    patient_id: uuid.UUID,
    *,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    training_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    professional_id: uuid.UUID | None,
) -> list[_TrialRow]:
    query = (
        db.query(Trial, ClinicalSession.id, ClinicalSession.occurred_at, Training.id, Training.title, TrainingCategory.name)
        .join(SessionTraining, Trial.session_training_id == SessionTraining.id)
        .join(ClinicalSession, SessionTraining.session_id == ClinicalSession.id)
        .join(Training, SessionTraining.training_id == Training.id)
        .join(TrainingCategory, Training.category_id == TrainingCategory.id)
        .filter(
            ClinicalSession.patient_id == patient_id,
            ClinicalSession.deleted_at.is_(None),
            Trial.deleted_at.is_(None),
        )
    )
    if date_from is not None:
        query = query.filter(ClinicalSession.occurred_at >= date_from)
    if date_to is not None:
        query = query.filter(ClinicalSession.occurred_at <= datetime.datetime.combine(date_to, datetime.time.max))
    if training_id is not None:
        query = query.filter(Training.id == training_id)
    if category_id is not None:
        query = query.filter(TrainingCategory.id == category_id)
    if professional_id is not None:
        query = query.filter(ClinicalSession.professional_id == professional_id)

    return [
        _TrialRow(trial, session_id, occurred_at.date(), training_pk, training_title, category_name)
        for trial, session_id, occurred_at, training_pk, training_title, category_name in query.all()
    ]


def _overall_accuracy(rows: list[_TrialRow]) -> float | None:
    return accuracy_pct([r.trial for r in rows])


def build_line_series(rows: list[_TrialRow]) -> list[dict]:
    """Seção 14.3 — evolução do percentual de acerto/independência ao longo das datas, por treino."""
    by_training: dict[uuid.UUID, dict] = {}
    for row in rows:
        by_training.setdefault(row.training_id, {"title": row.training_title, "by_date": collections.defaultdict(list)})
        by_training[row.training_id]["by_date"][row.session_date].append(row.trial)

    series = []
    for training_id, data in by_training.items():
        points = [
            {
                "date": d,
                "accuracy_pct": accuracy_pct(trials),
                "independence_pct": independence_pct(trials),
            }
            for d, trials in sorted(data["by_date"].items())
        ]
        series.append({"training_id": training_id, "training_title": data["title"], "points": points})
    return series


def build_bar_data(rows: list[_TrialRow]) -> list[dict]:
    """Seção 14.3 — comparação entre treinos no período filtrado."""
    by_training: dict[uuid.UUID, dict] = {}
    for row in rows:
        by_training.setdefault(row.training_id, {"title": row.training_title, "trials": []})
        by_training[row.training_id]["trials"].append(row.trial)

    return [
        {
            "training_id": tid,
            "training_title": data["title"],
            "accuracy_pct": accuracy_pct(data["trials"]),
            "sample_size": len(data["trials"]),
        }
        for tid, data in by_training.items()
    ]


def build_stacked_bar_data(rows: list[_TrialRow]) -> list[dict]:
    """Seção 14.3 — distribuição dos níveis de ajuda por sessão."""
    by_session: dict[uuid.UUID, dict] = {}
    for row in rows:
        by_session.setdefault(row.session_id, {"date": row.session_date, "trials": []})
        by_session[row.session_id]["trials"].append(row.trial)

    return [
        {
            "session_id": sid,
            "date": data["date"],
            "distribution_pct": prompt_level_distribution(data["trials"]),
        }
        for sid, data in sorted(by_session.items(), key=lambda kv: kv[1]["date"])
    ]


def build_pie_data(rows: list[_TrialRow]) -> dict:
    """Seção 14.3 — distribuição de correta/incorreta/parcial/não respondida."""
    counts = {"correct": 0, "incorrect": 0, "partial": 0, "no_response": 0}
    for row in rows:
        counts[row.trial.result.value] += 1
    return counts


def build_radar_data(rows: list[_TrialRow]) -> list[dict]:
    """Seção 14.3 — visão resumida por área, com alerta de limitações estatísticas."""
    by_category: dict[str, list] = collections.defaultdict(list)
    for row in rows:
        by_category[row.category_name].append(row.trial)

    return [
        {
            "area": category,
            "accuracy_pct": accuracy_pct(trials),
            "sample_size": len(trials),
            "insufficient_data": len(trials) < RADAR_MIN_SAMPLE_SIZE,
        }
        for category, trials in by_category.items()
    ]


def build_cumulative_data(rows: list[_TrialRow]) -> list[dict]:
    """Seção 14.3 — avanço acumulado e mudança da dependência de ajuda."""
    by_date: dict[datetime.date, list] = collections.defaultdict(list)
    for row in rows:
        by_date[row.session_date].append(row.trial)

    cumulative_correct = 0
    cumulative_independent = 0
    cumulative_total = 0
    points = []
    for d, trials in sorted(by_date.items()):
        for t in trials:
            cumulative_total += 1
            if t.result == TrialResult.CORRECT:
                cumulative_correct += 1
            if t.prompt_level.value == "independent":
                cumulative_independent += 1
        points.append(
            {
                "date": d,
                "cumulative_correct": cumulative_correct,
                "cumulative_total": cumulative_total,
                "cumulative_independence_pct": (
                    round(cumulative_independent / cumulative_total * 100, 1) if cumulative_total else None
                ),
            }
        )
    return points


def get_report_data(
    db: Session,
    user: User,
    patient_id: uuid.UUID,
    *,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    training_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    professional_id: uuid.UUID | None = None,
    compare_from: datetime.date | None = None,
    compare_to: datetime.date | None = None,
) -> dict:
    """Seção 14.1/14.2 — Reports usa as tentativas registradas em Sessions como fonte
    primária; nada aqui é agregado manualmente fora da coleta."""
    patient_service.get_patient_or_404(db, user, patient_id)

    rows = _fetch_rows(
        db,
        patient_id,
        date_from=date_from,
        date_to=date_to,
        training_id=training_id,
        category_id=category_id,
        professional_id=professional_id,
    )

    comparison = None
    if compare_from is not None and compare_to is not None:
        rows_a = rows
        rows_b = _fetch_rows(
            db,
            patient_id,
            date_from=compare_from,
            date_to=compare_to,
            training_id=training_id,
            category_id=category_id,
            professional_id=professional_id,
        )
        acc_a = _overall_accuracy(rows_a)
        acc_b = _overall_accuracy(rows_b)
        if acc_a is not None and acc_b is not None:
            comparison = {
                "available": True,
                "period_a_accuracy_pct": acc_a,
                "period_b_accuracy_pct": acc_b,
                "delta_pct": round(acc_b - acc_a, 1),
            }
        else:
            comparison = {"available": False, "message": "Dados insuficientes para comparação entre os períodos."}

    return {
        "patient_id": patient_id,
        "period_start": date_from,
        "period_end": date_to,
        "total_trials": len(rows),
        "line": build_line_series(rows),
        "bar": build_bar_data(rows),
        "stacked_bar": build_stacked_bar_data(rows),
        "pie": build_pie_data(rows),
        "radar": build_radar_data(rows),
        "cumulative": build_cumulative_data(rows),
        "comparison": comparison,
    }
