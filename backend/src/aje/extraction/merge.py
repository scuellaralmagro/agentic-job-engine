from aje.extraction.schema import CandidateProfile, ProfileData
from aje.llm.registry import llm_for

_SYSTEM = (
    "You merge a NEW candidate profile into an EXISTING profile. Deduplicate "
    "semantically (e.g. 'React' and 'ReactJS' are one skill), combine overlapping "
    "experiences, and keep all information. Preserve every existing source_refs value "
    "and union it with the new source id for any item the new source contributes to. "
    "Return the complete merged profile."
)


def _stamp(candidate: CandidateProfile, source_id: int) -> None:
    for collection in (
        candidate.skills,
        candidate.experiences,
        candidate.education,
        candidate.achievements,
        candidate.languages,
    ):
        for item in collection:
            if source_id not in item.source_refs:
                item.source_refs.append(source_id)


def merge_into_profile(
    existing: ProfileData, candidate: CandidateProfile, source_id: int
) -> ProfileData:
    _stamp(candidate, source_id)
    model = llm_for("extraction").with_structured_output(ProfileData)
    payload = (
        f"EXISTING:\n{existing.model_dump_json()}\n\n"
        f"NEW (source_id={source_id}):\n{candidate.model_dump_json()}"
    )
    return model.invoke([("system", _SYSTEM), ("human", payload)])
