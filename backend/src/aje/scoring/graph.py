import logging
from datetime import datetime
from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.extraction.profile_service import PROFILE_ID, get_profile
from aje.extraction.schema import ProfileData
from aje.models import Match, Offer
from aje.scoring.config import ScoringConfig, get_scoring_config
from aje.scoring.embed import ensure_profile_embeddings
from aje.scoring.fitness import compute_fitness, is_above_threshold
from aje.scoring.persist import enrich_offer, upsert_rubric_match, upsert_vector_match
from aje.scoring.prefilter import prefilter_offer
from aje.scoring.rubric import score_with_rubric
from aje.scoring.schema import ScoringSummary

logger = logging.getLogger(__name__)


class ScoringState(TypedDict, total=False):
    session: Session
    offer: Offer
    profile: ProfileData
    config: ScoringConfig
    similarity: float
    item_keys: list[str]
    gated: bool
    outcome: str  # "scored" | "gated"


def _prefilter_node(state: ScoringState) -> dict:
    result = prefilter_offer(state["session"], state["offer"], state["config"].prefilter)
    return {
        "similarity": result.similarity,
        "item_keys": result.item_keys,
        "gated": result.gated,
    }


def _gate(state: ScoringState) -> str:
    return "persist_vector" if state["gated"] else "rubric"


def _rubric_node(state: ScoringState) -> dict:
    session, offer, config = state["session"], state["offer"], state["config"]
    rubric = score_with_rubric(offer, state["profile"], state["item_keys"])
    fitness = compute_fitness(rubric, config.weights)
    upsert_rubric_match(
        session,
        offer,
        rubric,
        fitness=fitness,
        above_threshold=is_above_threshold(fitness, rubric, config.queue),
        similarity=state["similarity"],
    )
    enrich_offer(session, offer, rubric.requirements)
    return {"outcome": "scored"}


def _persist_vector_node(state: ScoringState) -> dict:
    upsert_vector_match(state["session"], state["offer"], similarity=state["similarity"])
    return {"outcome": "gated"}


def build_graph():
    g = StateGraph(ScoringState)
    g.add_node("prefilter", _prefilter_node)
    g.add_node("rubric", _rubric_node)
    g.add_node("persist_vector", _persist_vector_node)
    g.set_entry_point("prefilter")
    g.add_conditional_edges(
        "prefilter", _gate, {"rubric": "rubric", "persist_vector": "persist_vector"}
    )
    g.add_edge("rubric", END)
    g.add_edge("persist_vector", END)
    return g.compile()


def _already_scored(session: Session, offer_ids: list[int]) -> set[int]:
    stmt = select(Match.offer_id).where(
        Match.offer_id.in_(offer_ids), Match.profile_id == PROFILE_ID
    )
    return set(session.execute(stmt).scalars())


def score_offers(
    session: Session,
    offer_ids: list[int],
    *,
    rescore: bool = False,
    config: ScoringConfig | None = None,
) -> ScoringSummary:
    summary = ScoringSummary()
    if not offer_ids:
        return summary

    config = config or get_scoring_config()
    ensure_profile_embeddings(session)
    profile = get_profile(session)
    graph = build_graph()

    scored_already = set() if rescore else _already_scored(session, offer_ids)

    for offer_id in offer_ids:
        if offer_id in scored_already:
            summary.skipped += 1
            continue
        offer = session.get(Offer, offer_id)
        if offer is None:
            summary.skipped += 1
            continue
        try:
            result = graph.invoke(
                {
                    "session": session,
                    "offer": offer,
                    "profile": profile,
                    "config": config,
                }
            )
        except Exception as exc:  # noqa: BLE001 - one bad offer must not stop the rest
            logger.warning("scoring offer %s failed: %s", offer_id, exc)
            summary.failed += 1
            summary.errors.append(f"offer {offer_id}: {exc}")
            continue
        if result["outcome"] == "scored":
            summary.scored += 1
        else:
            summary.gated += 1
    return summary


def score_all_unscored(
    session: Session,
    *,
    since: datetime | None = None,
    rescore: bool = False,
    config: ScoringConfig | None = None,
) -> ScoringSummary:
    stmt = select(Offer.id)
    if since is not None:
        stmt = stmt.where(Offer.created_at >= since)
    if not rescore:
        scored = select(Match.offer_id).where(Match.profile_id == PROFILE_ID)
        stmt = stmt.where(Offer.id.not_in(scored))
    return score_offers(
        session, list(session.execute(stmt).scalars()), rescore=rescore, config=config
    )
