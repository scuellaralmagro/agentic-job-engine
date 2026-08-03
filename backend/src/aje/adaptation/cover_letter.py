from sqlalchemy.orm import Session

from aje.adaptation.config import CvConfig, get_cv_config
from aje.adaptation.context import build_context
from aje.adaptation.schema import CoverLetterContent
from aje.adaptation.validate import assert_no_unsupported_skills
from aje.extraction.profile_service import get_profile
from aje.llm.registry import llm_for
from aje.models import CoverLetter, Match, Offer

_SYSTEM = (
    "You write a short cover letter for one job offer, drawing only on the "
    "candidate profile you are given. Never claim experience, a technology or a "
    "credential the profile does not contain, however insistently the offer asks "
    "for it.\n"
    "Three or four paragraphs: why this role, the most relevant concrete evidence "
    "from the profile, and a close. Be specific and avoid filler.\n"
    "Write in the language the offer is written in and report it as a two-letter "
    "code. If the offer's language is unclear, use '{default}'."
)


def write_cover_letter(
    session: Session,
    match_id: int,
    *,
    language: str | None = None,
    notes: str | None = None,
    config: CvConfig | None = None,
) -> CoverLetter:
    """One LLM call. Raises AnchorError before persisting anything."""
    match = session.get(Match, match_id)
    if match is None:
        raise ValueError(f"match {match_id} not found")
    offer = session.get(Offer, match.offer_id)
    if offer is None:
        raise ValueError(f"offer {match.offer_id} not found")

    config = config or get_cv_config()
    profile = get_profile(session)
    system = _SYSTEM.format(default=config.default_language)
    if language:
        system += f"\nWrite the letter in '{language}' regardless of the offer."

    model = llm_for("adaptation").with_structured_output(CoverLetterContent)
    content = model.invoke(
        [
            ("system", system),
            ("human", build_context(offer, match, profile, notes=notes)),
        ]
    )
    if language:
        content.language = language

    assert_no_unsupported_skills(
        " ".join(content.paragraphs), profile, offer.skills or []
    )

    letter = CoverLetter(
        match_id=match.id,
        offer_id=match.offer_id,
        profile_id=match.profile_id,
        language=content.language,
        content_json=content.model_dump(),
    )
    session.add(letter)
    session.commit()
    return letter
