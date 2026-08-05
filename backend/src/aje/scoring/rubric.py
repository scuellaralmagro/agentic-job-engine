from aje.extraction.schema import ProfileData
from aje.llm.registry import llm_for
from aje.models import Offer
from aje.scoring.schema import RubricResult
from aje.scoring.texts import profile_item_texts

_SYSTEM = (
    "You assess how well a candidate fits a job offer. Score four dimensions from 0 to "
    "100 and justify each with concrete evidence taken from the candidate profile and "
    "the offer text.\n"
    "- skills: how much of the offer's required technical stack the candidate "
    "demonstrably has.\n"
    "- seniority: whether the candidate's years and scope of responsibility match what "
    "is asked.\n"
    "- domain: how close the candidate's industry and problem space is to the offer's.\n"
    "- language: whether the candidate meets the offer's stated language requirements.\n"
    "Set dealbreaker=true only for a hard blocker the candidate cannot resolve: a "
    "required work permit or nationality they lack, mandatory on-site presence in a "
    "country they are not in, or a required licence or degree they do not hold. Never "
    "set it merely for missing skills — those belong in gaps.\n"
    "Also extract the offer's own stated requirements (skills, seniority, languages) "
    "from the description.\n"
    "Answer in English regardless of the language the offer is written in."
)


def _render_profile(profile: ProfileData) -> str:
    """Complete and deterministic, so it is identical on every call.

    This block is the cacheable prefix (see `score_with_rubric`), which is why it
    renders the whole profile rather than the prefilter's per-offer selection: a
    selection that changes shape per offer changes the prefix and caches nothing.
    """
    sections = [
        "SKILLS: " + ", ".join(s.name for s in profile.skills),
        "LANGUAGES: "
        + ", ".join(
            f"{lang.name} ({lang.level})" if lang.level else lang.name
            for lang in profile.languages
        ),
        "EDUCATION: "
        + "; ".join(
            " ".join(p for p in (e.degree, e.field, e.institution) if p)
            for e in profile.education
        ),
        "EXPERIENCE AND ACHIEVEMENTS:",
        *(text for _, text in profile_item_texts(profile)),
    ]
    return "\n".join(sections)


def _render_offer(offer: Offer) -> str:
    header = " | ".join(p for p in (offer.title, offer.company, offer.location) if p)
    return f"{header}\n\n{offer.description or ''}"


def score_with_rubric(offer: Offer, profile: ProfileData) -> RubricResult:
    """One LLM call. Raises on failure — the caller isolates it per offer.

    Ordering is load-bearing, not cosmetic. This is the highest-volume call in the
    product and roughly three quarters of its spend, so the prompt is built stable
    part first: system, then the whole profile, and only then the offer. Everything
    ahead of the offer is byte-identical from one offer to the next and gets served
    from the provider's prompt cache. The offer must stay last — moving anything
    volatile above it pushes the shared prefix below the provider's minimum and the
    cache silently stops paying out.
    """
    model = llm_for("scoring").with_structured_output(RubricResult)
    human = (
        "=== CANDIDATE PROFILE ===\n"
        f"{_render_profile(profile)}\n\n"
        "=== JOB OFFER ===\n"
        f"{_render_offer(offer)}"
    )
    return model.invoke([("system", _SYSTEM), ("human", human)])
