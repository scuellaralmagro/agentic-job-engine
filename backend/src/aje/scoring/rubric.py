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


def _render_profile(profile: ProfileData, item_keys: list[str]) -> str:
    wanted = set(item_keys)
    selected = {key: text for key, text in profile_item_texts(profile) if key in wanted}
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
        "MOST RELEVANT EXPERIENCE AND ACHIEVEMENTS:",
        *selected.values(),
    ]
    return "\n".join(sections)


def _render_offer(offer: Offer) -> str:
    header = " | ".join(p for p in (offer.title, offer.company, offer.location) if p)
    return f"{header}\n\n{offer.description or ''}"


def score_with_rubric(
    offer: Offer, profile: ProfileData, item_keys: list[str]
) -> RubricResult:
    """One LLM call. Raises on failure — the caller isolates it per offer."""
    model = llm_for("scoring").with_structured_output(RubricResult)
    human = (
        "=== JOB OFFER ===\n"
        f"{_render_offer(offer)}\n\n"
        "=== CANDIDATE PROFILE ===\n"
        f"{_render_profile(profile, item_keys)}"
    )
    return model.invoke([("system", _SYSTEM), ("human", human)])
