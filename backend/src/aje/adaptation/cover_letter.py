import re

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
    "code. If the offer's language is unclear, use '{default}'.\n"
    "This is prose an employer reads. Write no bracketed references or citations "
    "of any kind. The salutation and closing are separate fields: the paragraphs "
    "carry the body only, and must not repeat the greeting."
)

# Only the anchor prefixes defined in aje.keys, so ordinary bracketed prose survives.
_ANCHOR = re.compile(
    r"\s*\[(?:experience|achievement|skill|education|language):[^\]]*\]"
)


def strip_anchor_tokens(text: str) -> str:
    """Remove profile anchor keys a model cited into prose.

    The context no longer shows keys to the letter writer, but models are
    stochastic and a leaked key renders straight into the employer's PDF.
    """
    cleaned = _ANCHOR.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def drop_repeated_salutation(salutation: str, paragraphs: list[str]) -> list[str]:
    """Drop a first paragraph that is only the greeting again.

    The template prints the salutation and then every paragraph, so a model that
    opens its body with the greeting renders it twice to the employer. Matched
    whole, not by prefix: a paragraph that merely opens with the greeting and
    continues into real content is prose the writer meant to keep.
    """
    if paragraphs and paragraphs[0].strip().casefold() == salutation.strip().casefold():
        return paragraphs[1:]
    return paragraphs


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
            (
                "human",
                build_context(offer, match, profile, notes=notes, cite_keys=False),
            ),
        ]
    )
    if language:
        content.language = language

    content.salutation = strip_anchor_tokens(content.salutation)
    content.paragraphs = [strip_anchor_tokens(p) for p in content.paragraphs]
    content.closing = strip_anchor_tokens(content.closing)
    content.paragraphs = drop_repeated_salutation(
        content.salutation, content.paragraphs
    )

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
