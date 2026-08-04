from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from aje.api.profile import get_db_session
from aje.models import Match, Offer
from aje.scoring import review
from aje.scoring.embed import rebuild_all_embeddings
from aje.scoring.graph import score_all_unscored, score_offers

router = APIRouter()


class ScoreIn(BaseModel):
    offer_ids: list[int] | None = None
    since: datetime | None = None
    rescore: bool = False


def _offer_out(offer: Offer | None) -> dict | None:
    if offer is None:
        return None
    return {
        "id": offer.id,
        "title": offer.title,
        "company": offer.company,
        "location": offer.location,
        "seniority": offer.seniority,
        "work_mode": offer.work_mode,
        "skills": offer.skills,
        "description": offer.description,
        "url": offer.url,
        "source": offer.source,
        "posted_at": offer.posted_at.isoformat() if offer.posted_at else None,
        "created_at": offer.created_at.isoformat(),
    }


def _scored_dimensions(rubric: dict | None) -> dict:
    """The stored rubric mixes scored dimensions with the dealbreaker flag and its
    reason. Consumers iterate `rubric` expecting every value to carry a score, so
    the non-dimension entries are split out rather than left to blow up a caller.
    Shape-based, not a hardcoded name list, so a new dimension needs no change here.
    """
    return {
        key: value
        for key, value in (rubric or {}).items()
        if isinstance(value, dict) and "score" in value
    }


def _match_out(session: Session, match: Match) -> dict:
    rubric = match.rubric or {}
    return {
        "id": match.id,
        "offer_id": match.offer_id,
        "offer": _offer_out(session.get(Offer, match.offer_id)),
        "fitness": match.fitness,
        "rubric": _scored_dimensions(rubric),
        "dealbreaker": bool(rubric.get("dealbreaker", False)),
        "dealbreaker_reason": rubric.get("dealbreaker_reason"),
        "gaps": match.gaps,
        "explanation": match.explanation,
        "above_threshold": match.above_threshold,
        "status": match.status,
        "scored_by": match.scored_by,
        "similarity": match.similarity,
        "scored_at": match.scored_at.isoformat() if match.scored_at else None,
    }


@router.get("/queue")
def read_queue(
    status: str = "new",
    min_fitness: float | None = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> list[dict]:
    matches = review.list_queue(
        session, status=status, min_fitness=min_fitness, limit=limit, offset=offset
    )
    return [_match_out(session, m) for m in matches]


@router.get("/matches/{match_id}")
def read_match(match_id: int, session: Session = Depends(get_db_session)) -> dict:
    match = review.get_match(session, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="match not found")
    return _match_out(session, match)


def _set_status(session: Session, match_id: int, status: str) -> dict:
    try:
        match = review.set_status(session, match_id, status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _match_out(session, match)


@router.post("/matches/{match_id}/accept")
def accept_match(match_id: int, session: Session = Depends(get_db_session)) -> dict:
    return _set_status(session, match_id, "accepted")


@router.post("/matches/{match_id}/dismiss")
def dismiss_match(match_id: int, session: Session = Depends(get_db_session)) -> dict:
    return _set_status(session, match_id, "dismissed")


@router.post("/matches/{match_id}/reset")
def reset_match(match_id: int, session: Session = Depends(get_db_session)) -> dict:
    return _set_status(session, match_id, "new")


@router.post("/score")
def run_scoring(body: ScoreIn, session: Session = Depends(get_db_session)) -> dict:
    try:
        if body.offer_ids:
            summary = score_offers(session, body.offer_ids, rescore=body.rescore)
        else:
            summary = score_all_unscored(session, since=body.since, rescore=body.rescore)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Scoring failed: {exc}")
    return summary.model_dump()


@router.post("/embeddings/rebuild")
def rebuild_embeddings(session: Session = Depends(get_db_session)) -> dict:
    try:
        return {"embedded": rebuild_all_embeddings(session)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Rebuild failed: {exc}")
