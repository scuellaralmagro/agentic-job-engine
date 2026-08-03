from aje.discovery.config import SourcesConfig
from aje.discovery.estimate import estimate_run
from aje.scoring.config import ScoringConfig


def test_estimate_is_a_ceiling_across_enabled_sources():
    """Offer counts cannot be predicted, so the estimate is the configured maximum."""
    sources = SourcesConfig.model_validate(
        {
            "sources": {
                "adzuna": {"enabled": True, "max_results": 50},
                "jobspy": {"enabled": True, "max_results": 30},
                "tecnoempleo": {"enabled": False, "max_results": 50},
            }
        }
    )

    est = estimate_run(sources=sources)

    assert est.max_offers == 80  # the disabled source is excluded
    assert est.max_cost_usd == round(80 * est.cost_per_offer_usd, 2)


def test_cost_per_offer_comes_from_config():
    """It changes whenever the scoring model changes, so it is not hardcoded."""
    scoring = ScoringConfig.model_validate({"estimate": {"cost_per_offer_usd": 0.05}})

    est = estimate_run(scoring=scoring)

    assert est.cost_per_offer_usd == 0.05
