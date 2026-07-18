from app.models.enums import PromptLevel, TrialResult
from app.models.session import Trial


def accuracy_pct(trials: list[Trial]) -> float | None:
    """Seção 14.4 — Percentual de acerto = respostas corretas / tentativas validas x 100.
    Tentativas excluidas por soft delete ja nao devem estar na lista recebida."""
    valid_trials = [t for t in trials if t.deleted_at is None]
    if not valid_trials:
        return None
    correct = sum(1 for t in valid_trials if t.result == TrialResult.CORRECT)
    return round(correct / len(valid_trials) * 100, 1)


def independence_pct(trials: list[Trial]) -> float | None:
    """Seção 14.4 — Percentual de independencia = tentativas independentes / tentativas validas x 100."""
    valid_trials = [t for t in trials if t.deleted_at is None]
    if not valid_trials:
        return None
    independent = sum(1 for t in valid_trials if t.prompt_level == PromptLevel.INDEPENDENT)
    return round(independent / len(valid_trials) * 100, 1)


def prompt_level_distribution(trials: list[Trial]) -> dict[str, float]:
    """Seção 14.4 — Distribuicao de ajuda = contagem de cada nivel / total de tentativas validas."""
    valid_trials = [t for t in trials if t.deleted_at is None]
    if not valid_trials:
        return {}
    total = len(valid_trials)
    counts: dict[str, int] = {}
    for t in valid_trials:
        counts[t.prompt_level.value] = counts.get(t.prompt_level.value, 0) + 1
    return {level: round(count / total * 100, 1) for level, count in counts.items()}
