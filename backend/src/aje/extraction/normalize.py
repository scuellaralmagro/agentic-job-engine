"""Everything enters the Profile in English, and structured the same way.

The Profile is the single source of truth that scoring and adaptation read from,
and merge dedups by name. A CV in Spanish and a LinkedIn export in Spanish would
otherwise produce "Desarrollo web" and "Web development" as two distinct skills.
"""

from aje.extraction.schema import CandidateProfile
from aje.llm.registry import llm_for

ENGLISH_RULE = (
    "Write every field in English, translating from the source language where "
    "needed. This includes job titles, skill names, descriptions, bullet points, "
    "degree and field names, achievements, the headline, and language names "
    "(e.g. 'Espanol' becomes 'Spanish'). Never translate proper nouns: keep "
    "people's names, company names, institution names, product names, "
    "technologies, email addresses, phone numbers and URLs exactly as written."
)

_SYSTEM = (
    "You are given a candidate profile that was read mechanically out of a "
    "LinkedIn data export, so it is raw: each role's whole description sits in a "
    "single unsplit bullet, no skills are attached to the experiences that "
    "demonstrate them, and the text is in whatever language the user wrote it in. "
    "Restructure it into the same clean shape a CV would produce.\n"
    "- Split each experience description into concrete, individual bullet points, "
    "one accomplishment or responsibility each. Drop filler that says nothing.\n"
    "- For each experience, populate `skills` with the technologies and skills "
    "that experience actually evidences, drawn only from its own text.\n"
    "- Keep every experience, education entry and language, in the order given.\n"
    "- Keep dates, levels and source_refs exactly as given.\n"
    "Do not invent anything that is not present in the input — this profile is a "
    "factual record the user will send to employers.\n" + ENGLISH_RULE
)


def structure_linkedin(candidate: CandidateProfile) -> CandidateProfile:
    """One LLM call. Raises on failure — the caller decides what that means."""
    model = llm_for("extraction").with_structured_output(CandidateProfile)
    return model.invoke([("system", _SYSTEM), ("human", candidate.model_dump_json())])
