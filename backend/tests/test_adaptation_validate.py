import pytest

from aje.adaptation.schema import TailoredBullet, TailoredCv, TailoredExperience
from aje.adaptation.validate import AnchorError, validate_projection
from aje.extraction.schema import Experience, ProfileData, Skill


def _profile() -> ProfileData:
    return ProfileData(
        skills=[Skill(name="Python"), Skill(name="FastAPI")],
        experiences=[
            Experience(
                company="Acme",
                title="Backend Engineer",
                bullets=["Built the billing API", "Mentored two juniors"],
            )
        ],
    )


def _cv(**overrides) -> TailoredCv:
    base = dict(
        language="en",
        headline="Backend Engineer",
        summary="Builds Python APIs.",
        experiences=[
            TailoredExperience(
                source_key="experience:acme|backend engineer",
                bullets=[
                    TailoredBullet(
                        source_key="experience:acme|backend engineer#bullet:0",
                        text="Built and owned the billing API",
                    )
                ],
            )
        ],
        skill_keys=["skill:python"],
    )
    base.update(overrides)
    return TailoredCv(**base)


def test_a_well_anchored_cv_passes():
    validate_projection(_cv(), _profile(), ["Python"])


def test_an_unknown_source_key_raises():
    cv = _cv(
        experiences=[
            TailoredExperience(
                source_key="experience:acme|backend engineer",
                bullets=[
                    TailoredBullet(
                        source_key="experience:acme|backend engineer#bullet:9",
                        text="Led the SRE team",
                    )
                ],
            )
        ]
    )

    with pytest.raises(AnchorError, match="not found in profile"):
        validate_projection(cv, _profile(), [])


def test_a_skill_key_the_profile_lacks_raises():
    with pytest.raises(AnchorError, match="not found in profile"):
        validate_projection(_cv(skill_keys=["skill:kubernetes"]), _profile(), [])


def test_a_missing_profile_experience_raises():
    with pytest.raises(AnchorError, match="missing from the CV"):
        validate_projection(_cv(experiences=[]), _profile(), [])


def test_an_offer_only_skill_in_the_summary_raises():
    cv = _cv(summary="Experienced Kubernetes engineer with strong Python skills.")

    with pytest.raises(AnchorError, match="Kubernetes"):
        validate_projection(cv, _profile(), ["Python", "Kubernetes"])


def test_an_offer_only_skill_in_the_headline_raises():
    cv = _cv(headline="Kubernetes Platform Engineer")

    with pytest.raises(AnchorError, match="Kubernetes"):
        validate_projection(cv, _profile(), ["Kubernetes"])


def test_a_skill_the_profile_does_have_may_appear_in_the_summary():
    cv = _cv(summary="Experienced Python and FastAPI engineer.")

    validate_projection(cv, _profile(), ["Python", "FastAPI"])


def test_a_skill_name_inside_a_longer_word_is_not_a_match():
    """'R' must not match 'React'; substring checks would make this unusable."""
    cv = _cv(summary="Strong Python background.")

    validate_projection(cv, _profile(), ["R", "Go"])
