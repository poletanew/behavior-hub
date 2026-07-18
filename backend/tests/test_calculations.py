import datetime
import uuid

from app.models.enums import PromptLevel, TrialResult
from app.models.session import Trial
from app.services.calculations import accuracy_pct, independence_pct, prompt_level_distribution


def _trial(result: TrialResult, prompt_level: PromptLevel, deleted: bool = False) -> Trial:
    return Trial(
        id=uuid.uuid4(),
        session_training_id=uuid.uuid4(),
        attempt_number=1,
        result=result,
        prompt_level=prompt_level,
        recorded_at=datetime.datetime.now(datetime.timezone.utc),
        deleted_at=datetime.datetime.now(datetime.timezone.utc) if deleted else None,
    )


def test_accuracy_pct_matches_prd_example():
    """Seção 14.4/33.1 — 2 corretas em 3 tentativas validas = 66,7%."""
    trials = [
        _trial(TrialResult.CORRECT, PromptLevel.INDEPENDENT),
        _trial(TrialResult.CORRECT, PromptLevel.VERBAL),
        _trial(TrialResult.INCORRECT, PromptLevel.GESTURAL),
    ]
    assert accuracy_pct(trials) == 66.7


def test_accuracy_pct_ignores_soft_deleted_trials():
    trials = [
        _trial(TrialResult.CORRECT, PromptLevel.INDEPENDENT),
        _trial(TrialResult.INCORRECT, PromptLevel.GESTURAL, deleted=True),
    ]
    assert accuracy_pct(trials) == 100.0


def test_accuracy_pct_with_no_valid_trials_is_none():
    assert accuracy_pct([]) is None
    assert accuracy_pct([_trial(TrialResult.CORRECT, PromptLevel.INDEPENDENT, deleted=True)]) is None


def test_independence_pct():
    trials = [
        _trial(TrialResult.CORRECT, PromptLevel.INDEPENDENT),
        _trial(TrialResult.CORRECT, PromptLevel.VERBAL),
        _trial(TrialResult.CORRECT, PromptLevel.INDEPENDENT),
        _trial(TrialResult.CORRECT, PromptLevel.GESTURAL),
    ]
    assert independence_pct(trials) == 50.0


def test_prompt_level_distribution_sums_to_100():
    trials = [
        _trial(TrialResult.CORRECT, PromptLevel.INDEPENDENT),
        _trial(TrialResult.CORRECT, PromptLevel.INDEPENDENT),
        _trial(TrialResult.INCORRECT, PromptLevel.VERBAL),
        _trial(TrialResult.PARTIAL, PromptLevel.FULL_PHYSICAL),
    ]
    distribution = prompt_level_distribution(trials)
    assert distribution["independent"] == 50.0
    assert distribution["verbal"] == 25.0
    assert distribution["full_physical"] == 25.0
    assert round(sum(distribution.values()), 1) == 100.0
