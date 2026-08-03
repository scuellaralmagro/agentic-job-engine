from aje.scoring.config import QueueSettings, Weights
from aje.scoring.schema import RubricResult


def compute_fitness(rubric: RubricResult, weights: Weights) -> float:
    """The model scores dimensions; the arithmetic stays here so weights can be
    retuned without re-running anything and the score survives a model swap."""
    total = (
        rubric.skills.score * weights.skills
        + rubric.seniority.score * weights.seniority
        + rubric.domain.score * weights.domain
        + rubric.language.score * weights.language
    )
    return round(total, 1)


def is_above_threshold(
    fitness: float, rubric: RubricResult, queue: QueueSettings
) -> bool:
    return fitness >= queue.threshold and not rubric.dealbreaker
