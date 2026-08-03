from sqlalchemy.orm import Session

from aje.adaptation.schema import AdaptationResult
from aje.models import CvProjection, Match, Offer


def projection_name(offer: Offer | None) -> str:
    if offer is None:
        return "Tailored CV"
    parts = [p for p in (offer.title, offer.company) if p]
    return " - ".join(parts) or f"offer {offer.id}"


def save_projection(
    session: Session, match: Match, result: AdaptationResult
) -> CvProjection:
    """Always inserts. Regenerating must not clobber a draft being edited."""
    offer = session.get(Offer, match.offer_id)
    projection = CvProjection(
        profile_id=match.profile_id,
        offer_id=match.offer_id,
        match_id=match.id,
        name=projection_name(offer),
        content_json=result.cv.model_dump(),
        suggestions=[s.model_dump() for s in result.suggestions],
        language=result.cv.language,
    )
    session.add(projection)
    session.commit()
    return projection
