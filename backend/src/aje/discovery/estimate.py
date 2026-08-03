"""Pre-run spend ceiling.

Not a forecast: how many offers a query returns is unknowable without running it.
This is the configured maximum across enabled sources, which is what the per-run
cap is measured against.
"""

from pydantic import BaseModel

from aje.discovery.config import SourcesConfig, get_sources_config
from aje.scoring.config import ScoringConfig, get_scoring_config


class RunEstimate(BaseModel):
    max_offers: int
    cost_per_offer_usd: float
    max_cost_usd: float


def estimate_run(
    sources: SourcesConfig | None = None, scoring: ScoringConfig | None = None
) -> RunEstimate:
    sources = sources or get_sources_config()
    scoring = scoring or get_scoring_config()

    max_offers = sum(
        sources.for_source(name).max_results for name in sources.enabled_names()
    )
    per_offer = scoring.estimate.cost_per_offer_usd
    return RunEstimate(
        max_offers=max_offers,
        cost_per_offer_usd=per_offer,
        max_cost_usd=round(max_offers * per_offer, 2),
    )
