"""Print the distribution of prefilter similarities over stored offers.

Run this once you have real offers, then set `prefilter.min_similarity` in
config/scoring.yaml from the output. It calls the real embeddings provider, so
it costs money — never run it from tests.

    cd backend && uv run python -m scripts.calibrate_threshold
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.db import get_session
from aje.llm.providers import register_default_providers
from aje.models import Offer
from aje.scoring.config import PrefilterSettings, get_scoring_config
from aje.scoring.embed import ensure_profile_embeddings
from aje.scoring.prefilter import prefilter_offer

_PERCENTILES = {"p10": 0.10, "p25": 0.25, "p50": 0.50, "p75": 0.75, "p90": 0.90}


def collect_similarities(
    session: Session, settings: PrefilterSettings
) -> list[tuple[int, str, float]]:
    rows: list[tuple[int, str, float]] = []
    for offer in session.execute(select(Offer)).scalars():
        result = prefilter_offer(session, offer, settings)
        rows.append((offer.id, offer.title, result.similarity))
    return rows


def percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    out = {"min": ordered[0], "max": ordered[-1]}
    for name, fraction in _PERCENTILES.items():
        index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
        out[name] = ordered[index]
    return out


def main() -> None:
    register_default_providers()
    session = get_session()
    try:
        settings = get_scoring_config().prefilter
        embedded = ensure_profile_embeddings(session)
        print(f"profile items embedded this run: {embedded}")

        rows = collect_similarities(session, settings)
        if not rows:
            print("no offers in the database — run a discovery search first")
            return

        stats = percentiles([sim for _, _, sim in rows])
        print(f"\n{len(rows)} offers scored")
        for name, value in stats.items():
            print(f"  {name:>4}: {value:.3f}")

        print("\nlowest 10 (these are what a cutoff would exclude):")
        for offer_id, title, sim in sorted(rows, key=lambda r: r[2])[:10]:
            print(f"  {sim:.3f}  #{offer_id} {title}")

        print("\nhighest 10:")
        for offer_id, title, sim in sorted(rows, key=lambda r: r[2], reverse=True)[:10]:
            print(f"  {sim:.3f}  #{offer_id} {title}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
