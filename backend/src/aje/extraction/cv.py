from aje.extraction.normalize import ENGLISH_RULE
from aje.extraction.schema import CandidateProfile
from aje.llm.registry import llm_for

_SYSTEM = (
    "You extract a candidate's CV into structured data. Capture the contact block "
    "(full name, professional headline, email, phone, city/country, and any profile "
    "links such as LinkedIn or GitHub), skills, work "
    "experiences (with bullet points and the skills each used), education, "
    "achievements, and languages. Do not invent information that is not present. "
    "Leave source_refs empty.\n"
    + ENGLISH_RULE
)


def extract_cv(text: str) -> CandidateProfile:
    model = llm_for("extraction").with_structured_output(CandidateProfile)
    return model.invoke([("system", _SYSTEM), ("human", text)])
