from aje.extraction.schema import (
    CandidateProfile,
    Experience,
    ProfileData,
    Skill,
)


def test_defaults_are_empty():
    p = ProfileData()
    assert p.skills == [] and p.experiences == []


def test_item_source_refs_default_empty():
    assert Skill(name="Python").source_refs == []


def test_candidate_profile_is_profiledata_shape():
    cp = CandidateProfile(
        skills=[Skill(name="Go")],
        experiences=[Experience(company="Acme", title="Dev")],
    )
    assert isinstance(cp, ProfileData)
    assert cp.skills[0].name == "Go"
    # dict coercion (JSON round-trip shape)
    round_tripped = ProfileData.model_validate(cp.model_dump())
    assert round_tripped.experiences[0].company == "Acme"
