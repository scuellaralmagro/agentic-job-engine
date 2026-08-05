import pytest

from aje.extraction.schema import Experience, Language, ProfileData, Skill
from aje.models import Offer
from aje.scoring import rubric as rubric_mod
from aje.scoring.schema import DimensionScore, Gap, OfferRequirements, RubricResult


class _FakeStructured:
    def __init__(self, result):
        self._result = result
        self.last_messages = None
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        self.last_messages = messages
        return self._result


class _FakeLLM:
    def __init__(self, result):
        self.structured = _FakeStructured(result)

    def with_structured_output(self, schema):
        return self.structured


def _result(**overrides):
    base = dict(
        skills=DimensionScore(score=80, evidence="Python everywhere"),
        seniority=DimensionScore(score=70, evidence="5 years"),
        domain=DimensionScore(score=60, evidence="Fintech adjacent"),
        language=DimensionScore(score=90, evidence="C1 English"),
        dealbreaker=False,
        dealbreaker_reason=None,
        gaps=[Gap(requirement="Kubernetes", severity="minor", profile_has="Docker")],
        requirements=OfferRequirements(
            skills=["Python"], seniority="senior", languages=["English"]
        ),
        explanation="Strong overall fit.",
    )
    base.update(overrides)
    return RubricResult(**base)


def _offer():
    return Offer(
        title="Senior Backend Engineer",
        company="Acme",
        location="Madrid",
        description="We need Python and Kubernetes.",
        source="test",
        content_hash="h",
    )


def _profile():
    return ProfileData(
        skills=[Skill(name="Python")],
        languages=[Language(name="English", level="C1")],
        experiences=[
            Experience(company="Acme", title="Backend Engineer", description="Payments")
        ],
    )


def test_returns_the_structured_rubric(monkeypatch):
    fake = _FakeLLM(_result())
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: fake)

    result = rubric_mod.score_with_rubric(_offer(), _profile())

    assert result.skills.score == 80
    assert result.requirements.seniority == "senior"
    assert fake.structured.calls == 1


def test_prompt_contains_the_offer_the_skills_and_the_experience(monkeypatch):
    fake = _FakeLLM(_result())
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: fake)

    rubric_mod.score_with_rubric(_offer(), _profile())

    human = fake.structured.last_messages[-1][1]
    assert "Senior Backend Engineer" in human
    assert "Python" in human  # full skill list, sent verbatim
    assert "English" in human  # full language list, sent verbatim
    assert "Backend Engineer" in human  # the experience


def test_every_experience_is_included(monkeypatch):
    """The profile block is complete, not a per-offer selection — see the prefix test."""
    fake = _FakeLLM(_result())
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: fake)
    profile = _profile()
    profile.experiences.append(Experience(company="Globex", title="Frontend Dev"))

    rubric_mod.score_with_rubric(_offer(), profile)

    human = fake.structured.last_messages[-1][1]
    assert "Globex" in human


def test_the_profile_precedes_the_offer(monkeypatch):
    fake = _FakeLLM(_result())
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: fake)

    rubric_mod.score_with_rubric(_offer(), _profile())

    human = fake.structured.last_messages[-1][1]
    assert human.index("=== CANDIDATE PROFILE ===") < human.index("=== JOB OFFER ===")


def test_everything_before_the_offer_is_identical_across_offers(monkeypatch):
    """The cache invariant. OpenAI caches on an exact prefix match, so every token
    ahead of the offer marker must be byte-identical from one offer to the next —
    otherwise the highest-volume call in the product caches nothing."""
    fake = _FakeLLM(_result())
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: fake)
    profile = _profile()

    rubric_mod.score_with_rubric(_offer(), profile)
    first = fake.structured.last_messages

    other = _offer()
    other.title = "Staff Platform Engineer"
    other.company = "Globex"
    other.description = "Go, Kafka and Terraform. Nothing like the first offer."
    rubric_mod.score_with_rubric(other, profile)
    second = fake.structured.last_messages

    assert first[0] == second[0]  # the system message
    marker = "=== JOB OFFER ==="
    assert first[-1][1].split(marker)[0] == second[-1][1].split(marker)[0]


def test_llm_failure_propagates(monkeypatch):
    def _boom(task):
        raise RuntimeError("llm down")

    monkeypatch.setattr(rubric_mod, "llm_for", _boom)

    # unlike query expansion, there is no useful degraded rubric — the caller
    # isolates this per offer instead
    with pytest.raises(RuntimeError):
        rubric_mod.score_with_rubric(_offer(), _profile())
