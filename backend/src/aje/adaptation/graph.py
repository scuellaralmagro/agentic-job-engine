from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from aje.adaptation.config import CvConfig, get_cv_config
from aje.adaptation.context import build_context
from aje.adaptation.draft import draft_cv
from aje.adaptation.persist import save_projection
from aje.adaptation.schema import AdaptationResult
from aje.adaptation.validate import validate_projection
from aje.extraction.profile_service import get_profile
from aje.extraction.schema import ProfileData
from aje.models import CvProjection, Match, Offer


class AdaptationState(TypedDict, total=False):
    session: Session
    match: Match
    offer: Offer
    profile: ProfileData
    config: CvConfig
    language: str | None
    notes: str | None
    context: str
    result: AdaptationResult
    projection: CvProjection


def _context_node(state: AdaptationState) -> dict:
    context = build_context(
        state["offer"], state["match"], state["profile"], notes=state.get("notes")
    )
    return {"context": context}


def _draft_node(state: AdaptationState) -> dict:
    result = draft_cv(
        state["context"], language=state.get("language"), config=state["config"]
    )
    return {"result": result}


def _validate_node(state: AdaptationState) -> dict:
    # raises AnchorError; nothing has been persisted at this point
    validate_projection(state["result"].cv, state["profile"], state["offer"].skills or [])
    return {}


def _persist_node(state: AdaptationState) -> dict:
    projection = save_projection(state["session"], state["match"], state["result"])
    return {"projection": projection}


def build_graph():
    g = StateGraph(AdaptationState)
    g.add_node("context", _context_node)
    g.add_node("draft", _draft_node)
    g.add_node("validate", _validate_node)
    g.add_node("persist", _persist_node)
    g.set_entry_point("context")
    g.add_edge("context", "draft")
    g.add_edge("draft", "validate")
    g.add_edge("validate", "persist")
    g.add_edge("persist", END)
    return g.compile()


def adapt_match(
    session: Session,
    match_id: int,
    *,
    language: str | None = None,
    notes: str | None = None,
    config: CvConfig | None = None,
) -> CvProjection:
    """Adapt the Profile to one scored offer. Raises AnchorError on a bad draft."""
    match = session.get(Match, match_id)
    if match is None:
        raise ValueError(f"match {match_id} not found")
    offer = session.get(Offer, match.offer_id)
    if offer is None:
        raise ValueError(f"offer {match.offer_id} not found")

    state = build_graph().invoke(
        {
            "session": session,
            "match": match,
            "offer": offer,
            "profile": get_profile(session),
            "config": config or get_cv_config(),
            "language": language,
            "notes": notes,
        }
    )
    return state["projection"]
