from datetime import datetime

from sqlalchemy.orm import Session

from aje.adaptation.config import CvConfig, get_cv_config
from aje.adaptation.render import (
    build_view,
    html_to_pdf,
    render_html,
    render_letter_html,
)
from aje.adaptation.schema import AdaptationResult, CoverLetterContent, TailoredCv
from aje.config import get_settings
from aje.extraction.profile_service import get_profile
from aje.models import CoverLetter, CvProjection, GeneratedDoc, Match, Offer


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


def save_generated_doc(
    session: Session,
    *,
    kind: str,
    offer_id: int | None,
    cv_projection_id: int | None,
    pdf_bytes: bytes,
    stem: str,
) -> GeneratedDoc:
    out_dir = get_settings().data_dir / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    dest = out_dir / f"{stem}-{stamp}.pdf"
    dest.write_bytes(pdf_bytes)
    doc = GeneratedDoc(
        kind=kind,
        offer_id=offer_id,
        cv_projection_id=cv_projection_id,
        pdf_ref=dest.as_posix(),
    )
    session.add(doc)
    session.commit()
    return doc


def render_projection(
    session: Session, projection_id: int, *, config: CvConfig | None = None
) -> GeneratedDoc:
    """Raises AnchorError if the projection references items the Profile has lost."""
    projection = session.get(CvProjection, projection_id)
    if projection is None:
        raise ValueError(f"projection {projection_id} not found")
    config = config or get_cv_config()

    cv = TailoredCv.model_validate(projection.content_json)
    view = build_view(cv, get_profile(session))
    pdf_bytes = html_to_pdf(render_html(view, config), config.page)

    return save_generated_doc(
        session,
        kind="cv",
        offer_id=projection.offer_id,
        cv_projection_id=projection.id,
        pdf_bytes=pdf_bytes,
        stem=f"cv-{projection.id}",
    )


def render_cover_letter(
    session: Session, letter_id: int, *, config: CvConfig | None = None
) -> GeneratedDoc:
    letter = session.get(CoverLetter, letter_id)
    if letter is None:
        raise ValueError(f"cover letter {letter_id} not found")
    config = config or get_cv_config()

    offer = session.get(Offer, letter.offer_id) if letter.offer_id else None
    offer_line = (
        " - ".join(p for p in (offer.title, offer.company) if p) if offer else ""
    )
    content = CoverLetterContent.model_validate(letter.content_json)
    html = render_letter_html(content, get_profile(session).contact, offer_line, config)

    return save_generated_doc(
        session,
        kind="cover_letter",
        offer_id=letter.offer_id,
        cv_projection_id=None,
        pdf_bytes=html_to_pdf(html, config.page),
        stem=f"cover-letter-{letter.id}",
    )
