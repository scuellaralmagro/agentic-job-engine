from aje.scoring.config import QueueSettings, Weights
from aje.scoring.fitness import compute_fitness, is_above_threshold
from aje.scoring.schema import DimensionScore, RubricResult


def _rubric(skills=80, seniority=70, domain=60, language=90, dealbreaker=False):
    return RubricResult(
        skills=DimensionScore(score=skills, evidence=""),
        seniority=DimensionScore(score=seniority, evidence=""),
        domain=DimensionScore(score=domain, evidence=""),
        language=DimensionScore(score=language, evidence=""),
        dealbreaker=dealbreaker,
    )


def test_fitness_is_the_weighted_average():
    weights = Weights(skills=0.5, seniority=0.2, domain=0.2, language=0.1)

    # 80*.5 + 70*.2 + 60*.2 + 90*.1 = 40 + 14 + 12 + 9
    assert compute_fitness(_rubric(), weights) == 75.0


def test_all_perfect_scores_give_one_hundred():
    assert compute_fitness(_rubric(100, 100, 100, 100), Weights()) == 100.0


def test_weights_change_the_result_without_touching_the_prompt():
    # 80*.7 + 70*.1 + 60*.1 + 90*.1 = 56 + 7 + 6 + 9
    skills_heavy = Weights(skills=0.7, seniority=0.1, domain=0.1, language=0.1)
    assert compute_fitness(_rubric(), skills_heavy) == 78.0


def test_above_threshold_when_score_clears_it():
    assert is_above_threshold(75.0, _rubric(), QueueSettings(threshold=60)) is True


def test_below_threshold_when_score_does_not():
    assert is_above_threshold(55.0, _rubric(), QueueSettings(threshold=60)) is False


def test_dealbreaker_keeps_a_high_score_out_of_the_queue():
    rubric = _rubric(100, 100, 100, 100, dealbreaker=True)
    # a hard blocker is a flag, not a quiet subtraction from the number
    assert compute_fitness(rubric, Weights()) == 100.0
    assert is_above_threshold(100.0, rubric, QueueSettings(threshold=60)) is False
