from pydantic import BaseModel
from sqlalchemy.orm import Session

from aje.models import Offer
from aje.scoring.config import PrefilterSettings
from aje.scoring.embed import ensure_offer_embeddings, similar_profile_items


class PrefilterResult(BaseModel):
    similarity: float
    item_keys: list[str]
    gated: bool


def prefilter_offer(
    session: Session, offer: Offer, settings: PrefilterSettings
) -> PrefilterResult:
    """Cheap 'is this offer even in my professional universe?' check.

    Not a fit judgement — it runs before the rubric and therefore has no
    extracted offer requirements to reason about. It exists to keep obviously
    unrelated postings from costing an LLM call.
    """
    offer_vectors = ensure_offer_embeddings(session, offer, settings.chunk_chars)

    best_per_item: dict[str, float] = {}
    for vector in offer_vectors:
        for item_key, similarity in similar_profile_items(session, vector, settings.top_k):
            if similarity > best_per_item.get(item_key, -1.0):
                best_per_item[item_key] = similarity

    if not best_per_item:
        # no profile vectors yet: pass everything rather than empty the queue
        return PrefilterResult(similarity=0.0, item_keys=[], gated=False)

    ranked = sorted(best_per_item.items(), key=lambda kv: kv[1], reverse=True)[
        : settings.top_k
    ]
    score = sum(sim for _, sim in ranked) / len(ranked)
    return PrefilterResult(
        similarity=score,
        item_keys=[key for key, _ in ranked],
        gated=score < settings.min_similarity,
    )
