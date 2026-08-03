import pytest

from aje.extraction.profile_service import save_profile
from aje.extraction.schema import Experience, ProfileData, Skill
from aje.models import Match, Offer
from aje.scoring import embed as embed_mod
from aje.scoring import graph as graph_mod
from aje.scoring import rubric as rubric_mod
from aje.scoring.config import PrefilterSettings, QueueSettings, ScoringConfig, Weights
from aje.scoring.schema import DimensionScore, OfferRequirements, RubricResult
from tests.fakes import FakeEmbeddings


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
        return self._result


def _rubric(skills=80, dealbreaker=False):
    return RubricResult(
        skills=DimensionScore(score=skills, evidence=""),
        seniority=DimensionScore(score=70, evidence=""),
        domain=DimensionScore(score=60, evidence=""),
        language=DimensionScore(score=90, evidence=""),
        dealbreaker=dealbreaker,
        requirements=OfferRequirements(skills=["Python"], seniority="senior"),
        explanation="ok",
    )


def _config(min_similarity=0.3, threshold=60):
    return ScoringConfig(
        weights=Weights(),
        prefilter=PrefilterSettings(min_similarity=min_similarity, top_k=4),
        queue=QueueSettings(threshold=threshold),
    )


@pytest.fixture
def fake_embeddings(monkeypatch):
    fake = FakeEmbeddings()
    monkeypatch.setattr(embed_mod, "embeddings_for", lambda task: fake)
    return fake


@pytest.fixture
def profile(session):
    save_profile(
        session,
        ProfileData(
            skills=[Skill(name="Python")],
            experiences=[
                Experience(
                    company="Acme",
                    title="Backend Engineer",
                    description="python fastapi postgres kubernetes",
                )
            ],
        ),
    )


def _offer(session, title, description, content_hash):
    offer = Offer(
        title=title,
        description=description,
        source="test",
        content_hash=content_hash,
        skills=[],
    )
    session.add(offer)
    session.commit()
    return offer


def test_relevant_offer_is_rubric_scored_and_enriched(
    session, fake_embeddings, profile, monkeypatch
):
    llm = _CountingLLM(_rubric())
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: llm)
    offer = _offer(session, "Backend Engineer", "python fastapi postgres", "h1")

    summary = graph_mod.score_offers(session, [offer.id], config=_config())

    assert summary.scored == 1 and summary.gated == 0
    match = session.query(Match).one()
    assert match.scored_by == "rubric"
    assert match.fitness == 75.0
    assert match.above_threshold is True
    assert session.get(Offer, offer.id).seniority == "senior"


def test_gated_offer_costs_no_llm_call(session, fake_embeddings, profile, monkeypatch):
    llm = _CountingLLM(_rubric())
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: llm)
    offer = _offer(session, "Nurse", "nurse sales", "h2")

    summary = graph_mod.score_offers(session, [offer.id], config=_config())

    # the single most important assertion in this suite: the gate protects the bill
    assert llm.calls == 0
    assert summary.gated == 1 and summary.scored == 0
    assert session.query(Match).one().scored_by == "vector"


def test_a_failing_offer_does_not_abort_the_rest(
    session, fake_embeddings, profile, monkeypatch
):
    llm = _CountingLLM(RuntimeError("llm down"))
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: llm)
    good = _offer(session, "Nurse", "nurse sales", "h3")  # gated, always succeeds
    bad = _offer(session, "Backend Engineer", "python fastapi", "h4")

    summary = graph_mod.score_offers(session, [bad.id, good.id], config=_config())

    assert summary.failed == 1
    assert summary.gated == 1
    assert summary.errors and "llm down" in summary.errors[0]


def test_already_scored_offers_are_skipped_unless_rescoring(
    session, fake_embeddings, profile, monkeypatch
):
    llm = _CountingLLM(_rubric())
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: llm)
    offer = _offer(session, "Backend Engineer", "python fastapi", "h5")
    graph_mod.score_offers(session, [offer.id], config=_config())

    skipped = graph_mod.score_offers(session, [offer.id], config=_config())
    assert skipped.skipped == 1 and llm.calls == 1

    rescored = graph_mod.score_offers(session, [offer.id], config=_config(), rescore=True)
    assert rescored.scored == 1 and llm.calls == 2


def test_dealbreaker_keeps_the_offer_out_of_the_queue(
    session, fake_embeddings, profile, monkeypatch
):
    llm = _CountingLLM(_rubric(skills=100, dealbreaker=True))
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: llm)
    offer = _offer(session, "Backend Engineer", "python fastapi", "h6")

    graph_mod.score_offers(session, [offer.id], config=_config())

    assert session.query(Match).one().above_threshold is False


def test_score_all_unscored_picks_up_everything_without_a_match(
    session, fake_embeddings, profile, monkeypatch
):
    llm = _CountingLLM(_rubric())
    monkeypatch.setattr(rubric_mod, "llm_for", lambda task: llm)
    _offer(session, "Backend Engineer", "python fastapi", "h7")
    _offer(session, "Nurse", "nurse sales", "h8")

    summary = graph_mod.score_all_unscored(session, config=_config())

    assert summary.scored == 1 and summary.gated == 1
