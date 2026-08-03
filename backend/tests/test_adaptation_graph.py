import pytest

from aje.adaptation import draft as draft_mod
from aje.adaptation import graph as graph_mod
from aje.adaptation.config import CvConfig
from aje.adaptation.schema import (
    AdaptationResult,
    Suggestion,
    TailoredBullet,
    TailoredCv,
    TailoredExperience,
)
from aje.adaptation.validate import AnchorError
from aje.extraction.profile_service import save_profile
from aje.extraction.schema import Contact, Experience, ProfileData, Skill
from aje.models import CvProjection, Match, Offer

EXP_KEY = "experience:acme|backend engineer"


class _CountingLLM:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        self.calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return self._result.model_copy(deep=True)


@pytest.fixture
def profile(session):
    save_profile(
        session,
        ProfileData(
            contact=Contact(full_name="Ada Lovelace", email="ada@example.com"),
            skills=[Skill(name="Python")],
            experiences=[
                Experience(
                    company="Acme",
                    title="Backend Engineer",
                    bullets=["Built the billing API"],
                )
            ],
        ),
    )


@pytest.fixture
def match(session):
    offer = Offer(
        title="Senior Backend Engineer",
        company="Globex",
        description="Python and API design.",
        source="test",
        content_hash="h1",
        skills=["Python"],
    )
    session.add(offer)
    session.commit()
    row = Match(offer_id=offer.id, profile_id=1, fitness=78.0, status="accepted")
    session.add(row)
    session.commit()
    return row


def _result(**cv_overrides) -> AdaptationResult:
    cv = dict(
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
    )
    cv.update(cv_overrides)
    return AdaptationResult(
        cv=TailoredCv(**cv),
        suggestions=[
            Suggestion(
                kind="rewrite",
                source_key=f"{EXP_KEY}#bullet:0",
                before="Built the billing API",
                after="Owned the billing API",
                reason="Offer emphasises ownership",
            )
        ],
    )


def _install(monkeypatch, result):
    llm = _CountingLLM(result)
    monkeypatch.setattr(draft_mod, "llm_for", lambda task: llm)
    return llm


def test_adapting_a_match_persists_a_projection(session, profile, match, monkeypatch):
    llm = _install(monkeypatch, _result())

    projection = graph_mod.adapt_match(session, match.id, config=CvConfig())

    assert llm.calls == 1
    assert projection.content_json["headline"] == "Backend Engineer"
    assert projection.suggestions[0]["kind"] == "rewrite"
    assert projection.match_id == match.id


def test_a_hallucinated_key_persists_nothing(session, profile, match, monkeypatch):
    _install(
        monkeypatch,
        _result(
            experiences=[
                TailoredExperience(
                    source_key=EXP_KEY,
                    bullets=[
                        TailoredBullet(
                            source_key=f"{EXP_KEY}#bullet:7", text="Led the SRE team"
                        )
                    ],
                )
            ]
        ),
    )

    with pytest.raises(AnchorError):
        graph_mod.adapt_match(session, match.id, config=CvConfig())

    assert session.query(CvProjection).count() == 0


def test_a_dropped_experience_persists_nothing(session, profile, match, monkeypatch):
    _install(monkeypatch, _result(experiences=[]))

    with pytest.raises(AnchorError):
        graph_mod.adapt_match(session, match.id, config=CvConfig())

    assert session.query(CvProjection).count() == 0


def test_an_offer_skill_the_profile_lacks_is_caught(session, profile, match, monkeypatch):
    session.query(Offer).one().skills = ["Python", "Kubernetes"]
    session.commit()
    _install(monkeypatch, _result(summary="Seasoned Kubernetes operator."))

    with pytest.raises(AnchorError, match="Kubernetes"):
        graph_mod.adapt_match(session, match.id, config=CvConfig())

    assert session.query(CvProjection).count() == 0


def test_regenerating_adds_a_second_projection(session, profile, match, monkeypatch):
    _install(monkeypatch, _result())

    graph_mod.adapt_match(session, match.id, config=CvConfig())
    graph_mod.adapt_match(session, match.id, config=CvConfig())

    assert session.query(CvProjection).count() == 2


def test_an_unknown_match_raises_value_error(session, profile, monkeypatch):
    _install(monkeypatch, _result())

    with pytest.raises(ValueError, match="match 999 not found"):
        graph_mod.adapt_match(session, 999, config=CvConfig())


def test_the_language_override_reaches_the_projection(session, profile, match, monkeypatch):
    _install(monkeypatch, _result())

    projection = graph_mod.adapt_match(
        session, match.id, language="es", config=CvConfig()
    )

    assert projection.language == "es"
