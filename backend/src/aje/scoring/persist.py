from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from aje.extraction.profile_service import PROFILE_ID
from aje.models import Match, Offer
from aje.scoring.schema import OfferRequirements, RubricResult


def _get_or_create(session: Session, offer_id: int) -> Match:
    stmt = select(Match).where(
        Match.offer_id == offer_id, Match.profile_id == PROFILE_ID
    )
    match = session.execute(stmt).scalar_one_or_none()
    if match is None:
        # status defaults to "new" here and is never touched again by scoring,
        # so an accept/dismiss survives every rescore
        match = Match(offer_id=offer_id, profile_id=PROFILE_ID, status="new")
        session.add(match)
    return match


def upsert_rubric_match(
    session: Session,
    offer: Offer,
    rubric: RubricResult,
    *,
    fitness: float,
    above_threshold: bool,
    similarity: float,
) -> Match:
    match = _get_or_create(session, offer.id)
    match.fitness = fitness
    match.rubric = rubric.model_dump(exclude={"gaps", "requirements", "explanation"})
    match.gaps = [gap.model_dump() for gap in rubric.gaps]
    match.explanation = rubric.explanation
    match.above_threshold = above_threshold
    match.similarity = similarity
    match.scored_by = "rubric"
    match.scored_at = datetime.utcnow()
    session.commit()
    return match


def upsert_vector_match(session: Session, offer: Offer, *, similarity: float) -> Match:
    match = _get_or_create(session, offer.id)
    match.fitness = round(similarity * 100, 1)
    match.rubric = {}
    match.gaps = []
    match.explanation = None
    match.above_threshold = False
    match.similarity = similarity
    match.scored_by = "vector"
    match.scored_at = datetime.utcnow()
    session.commit()
    return match


def enrich_offer(
    session: Session, offer: Offer, requirements: OfferRequirements
) -> None:
    """Fill the columns Discovery deliberately left empty. Never blanks data."""
    if requirements.skills:
        offer.skills = requirements.skills
    if requirements.seniority:
        offer.seniority = requirements.seniority
    session.commit()
