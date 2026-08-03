import json
from pathlib import Path

import pytest

from aje.scoring.config import load_scoring_config
from aje.scoring.fitness import compute_fitness, is_above_threshold
from aje.scoring.schema import RubricResult

GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_matches.json").read_text(
        encoding="utf-8"
    )
)


@pytest.fixture(scope="module")
def config():
    # the real shipped config, so a weight edit that changes queue membership
    # fails here instead of surprising you three weeks later
    return load_scoring_config(Path("config/scoring.yaml"))


@pytest.mark.parametrize("case", GOLDEN, ids=[c["name"] for c in GOLDEN])
def test_golden_fitness_is_stable(case, config):
    rubric = RubricResult.model_validate(case["rubric"])

    fitness = compute_fitness(rubric, config.weights)

    assert fitness == pytest.approx(case["expected_fitness"])


@pytest.mark.parametrize("case", GOLDEN, ids=[c["name"] for c in GOLDEN])
def test_golden_queue_membership_is_stable(case, config):
    rubric = RubricResult.model_validate(case["rubric"])
    fitness = compute_fitness(rubric, config.weights)

    assert (
        is_above_threshold(fitness, rubric, config.queue)
        is case["expected_above_threshold"]
    )
