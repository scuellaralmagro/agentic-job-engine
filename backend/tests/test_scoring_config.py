import pytest

from aje.scoring.config import ScoringConfig, load_scoring_config


def test_loads_weights_and_thresholds(tmp_path):
    path = tmp_path / "scoring.yaml"
    path.write_text(
        "weights: { skills: 0.5, seniority: 0.2, domain: 0.2, language: 0.1 }\n"
        "prefilter: { min_similarity: 0.30, top_k: 8, chunk_chars: 800 }\n"
        "queue: { threshold: 60 }\n",
        encoding="utf-8",
    )

    cfg = load_scoring_config(path)

    assert cfg.weights.skills == 0.5
    assert cfg.prefilter.min_similarity == 0.30
    assert cfg.prefilter.top_k == 8
    assert cfg.queue.threshold == 60


def test_weights_that_do_not_sum_to_one_are_rejected(tmp_path):
    path = tmp_path / "scoring.yaml"
    path.write_text(
        "weights: { skills: 0.9, seniority: 0.2, domain: 0.2, language: 0.1 }\n",
        encoding="utf-8",
    )

    # catching this at load time means a bad edit fails loudly instead of
    # silently producing fitness values above 100
    with pytest.raises(ValueError, match="sum to 1.0"):
        load_scoring_config(path)


def test_defaults_apply_when_sections_are_missing(tmp_path):
    path = tmp_path / "scoring.yaml"
    path.write_text(
        "weights: { skills: 0.5, seniority: 0.2, domain: 0.2, language: 0.1 }\n",
        encoding="utf-8",
    )

    cfg = load_scoring_config(path)

    assert cfg.prefilter.top_k == 8
    assert cfg.queue.threshold == 60


def test_empty_file_yields_all_defaults():
    cfg = ScoringConfig()
    assert cfg.weights.skills == 0.5
    assert cfg.prefilter.chunk_chars == 800
