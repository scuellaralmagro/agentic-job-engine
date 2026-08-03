import pytest

from aje.adaptation.render import build_view
from aje.adaptation.schema import TailoredBullet, TailoredCv, TailoredExperience
from aje.adaptation.validate import AnchorError
from aje.extraction.schema import (
    Achievement,
    Contact,
    Education,
    Experience,
    Language,
    ProfileData,
    Skill,
)
from aje.keys import achievement_key

EXP_KEY = "experience:acme|backend engineer"


def _profile() -> ProfileData:
    return ProfileData(
        contact=Contact(full_name="Ada Lovelace", email="ada@example.com"),
        skills=[Skill(name="Python"), Skill(name="FastAPI")],
        experiences=[
            Experience(
                company="Acme",
                title="Backend Engineer",
                start="2021",
                end="2024",
                bullets=["Built the billing API"],
            )
        ],
        education=[Education(institution="UC3M", degree="Ingenieria", field="Software")],
        achievements=[Achievement(text="Speaker at PyConES")],
        languages=[Language(name="English", level="C1")],
    )


def _cv(**overrides) -> TailoredCv:
    base = dict(
        language="en",
        headline="Backend Engineer",
        summary="Builds Python APIs.",
        experiences=[
            TailoredExperience(
                source_key=EXP_KEY,
                bullets=[
                    TailoredBullet(
                        source_key=f"{EXP_KEY}#bullet:0", text="Owned the billing API"
                    )
                ],
            )
        ],
        skill_keys=["skill:python"],
        achievement_keys=[achievement_key("Speaker at PyConES")],
        education_keys=["education:uc3m|ingenieria"],
        language_keys=["language:english"],
    )
    base.update(overrides)
    return TailoredCv(**base)


def test_the_view_carries_resolved_text_and_no_keys():
    view = build_view(_cv(), _profile())

    assert view.contact.full_name == "Ada Lovelace"
    assert view.skills == ["Python"]
    assert view.achievements == ["Speaker at PyConES"]
    assert view.education == ["Ingenieria Software UC3M"]
    assert view.languages == ["English (C1)"]


def test_experience_text_comes_from_the_tailored_bullets_not_the_profile():
    view = build_view(_cv(), _profile())

    assert view.experiences[0].title == "Backend Engineer"
    assert view.experiences[0].company == "Acme"
    assert view.experiences[0].period == "2021 - 2024"
    assert view.experiences[0].bullets == ["Owned the billing API"]


def test_selection_order_is_preserved():
    view = build_view(_cv(skill_keys=["skill:fastapi", "skill:python"]), _profile())

    assert view.skills == ["FastAPI", "Python"]


def test_an_unresolvable_key_raises_rather_than_disappearing():
    with pytest.raises(AnchorError, match="skill:kubernetes"):
        build_view(_cv(skill_keys=["skill:kubernetes"]), _profile())


def test_an_unresolvable_experience_key_raises():
    cv = _cv(experiences=[TailoredExperience(source_key="experience:globex|cto")])

    with pytest.raises(AnchorError, match=r"experience:globex\|cto"):
        build_view(cv, _profile())
