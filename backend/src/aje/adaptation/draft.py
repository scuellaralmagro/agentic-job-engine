from aje.adaptation.config import CvConfig
from aje.adaptation.schema import AdaptationResult
from aje.llm.registry import llm_for

_SYSTEM = (
    "You tailor a candidate's CV to one job offer. The CV must be a projection of "
    "the candidate profile you are given: you may select, reorder, emphasise and "
    "rephrase its content, but you may never add a fact it does not contain.\n"
    "Every element you output carries the source_key of the profile item it came "
    "from. Copy those keys verbatim from the brackets in the profile listing. An "
    "invented key is rejected and the entire draft discarded.\n"
    "Include EVERY experience in the profile — an omitted job reads as an "
    "unexplained employment gap. De-emphasise a weak one by keeping fewer bullets, "
    "never by dropping it. Order experiences by relevance to the offer.\n"
    "Keep at most {max_bullets} bullets per experience.\n"
    "The headline and summary are the only free prose. They must not name any "
    "technology the profile does not list, however insistently the offer asks for "
    "it.\n"
    "Write the CV in the language the offer is written in and report that language "
    "as a two-letter code in `language`. If the offer's language is unclear, use "
    "'{default}'.\n"
    "Return one suggestion per decision you made. `kind` is one of 'rewrite', "
    "'promote', 'demote', 'drop' or 'emphasize'; `before` and `after` show the "
    "change; `reason` cites something concrete in the offer."
)


def draft_cv(
    context: str, *, language: str | None, config: CvConfig
) -> AdaptationResult:
    """One LLM call. Raises on failure — the caller decides what that means."""
    system = _SYSTEM.format(
        max_bullets=config.max_bullets_per_experience,
        default=config.default_language,
    )
    if language:
        system += f"\nWrite the CV in '{language}' regardless of the offer's language."
    model = llm_for("adaptation").with_structured_output(AdaptationResult)
    result = model.invoke([("system", system), ("human", context)])
    if language:
        # deterministic: the caller's override wins even if the model ignored it
        result.cv.language = language
    return result
