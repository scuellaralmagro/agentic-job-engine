from aje.adaptation.context import build_context, render_profile_with_keys
from aje.extraction.schema import (
    Achievement,
    Education,
    Experience,
    Language,
    ProfileData,
    Skill,
)
from aje.keys import profile_keys
from aje.models import Match, Offer


def _profile() -> ProfileData:
    return ProfileData(
        skills=[Skill(name="Python")],
        experiences=[
            Experience(
                company="Acme",
                title="Backend Engineer",
                description="Owned the billing API",
                bullets=["Cut p99 latency"],
                start="2021",
                end="2024",
            )
        ],
        education=[Education(institution="UC3M", degree="Ingenieria")],
        achievements=[Achievement(text="Speaker at PyConES")],
        languages=[Language(name="English", level="C1")],
    )


def _offer() -> Offer:
    return Offer(
        id=7,
        title="Senior Backend Engineer",
        company="Globex",
        location="Madrid",
        description="We need Python and strong API design.",
        source="test",
        content_hash="h1",
        skills=["Python"],
    )


def _match() -> Match:
    return Match(
        id=3,
        offer_id=7,
        fitness=78.0,
        explanation="Strong backend overlap.",
        gaps=[{"requirement": "Kubernetes", "severity": "major", "profile_has": "Docker"}],
    )


def test_every_profile_key_appears_in_the_rendering():
    """The model can only cite keys it can see."""
    profile = _profile()
    rendered = render_profile_with_keys(profile)

    for key in profile_keys(profile):
        assert f"[{key}]" in rendered


def test_rendering_keeps_the_human_readable_text():
    rendered = render_profile_with_keys(_profile())

    assert "Cut p99 latency" in rendered
    assert "Backend Engineer" in rendered
    assert "English (C1)" in rendered


def test_context_carries_the_offer_the_assessment_and_the_profile():
    context = build_context(_offer(), _match(), _profile())

    assert "Senior Backend Engineer" in context
    assert "strong API design" in context
    assert "Strong backend overlap." in context
    assert "Kubernetes" in context  # the gap
    assert "[skill:python]" in context


def test_notes_are_included_only_when_given():
    with_notes = build_context(_offer(), _match(), _profile(), notes="Stress the fintech bit")
    without = build_context(_offer(), _match(), _profile())

    assert "USER NOTES" in with_notes
    assert "Stress the fintech bit" in with_notes
    assert "USER NOTES" not in without
