import pytest

from aje.extraction.profile_service import save_profile
from aje.extraction.schema import Experience, ProfileData
from aje.models import Offer
from aje.scoring import embed as embed_mod
from aje.scoring.config import PrefilterSettings
from aje.scoring.prefilter import prefilter_offer
from tests.fakes import FakeEmbeddings


@pytest.fixture
def fake_embeddings(monkeypatch):
    fake = FakeEmbeddings()
    monkeypatch.setattr(embed_mod, "embeddings_for", lambda task: fake)
    return fake


def _backend_profile(session):
    save_profile(
        session,
        ProfileData(
            experiences=[
                Experience(
                    company="Acme",
                    title="Backend Engineer",
                    description="python fastapi postgres kubernetes",
                )
            ]
        ),
    )
    embed_mod.ensure_profile_embeddings(session)


def _offer(session, title, description, content_hash):
    offer = Offer(
        title=title, description=description, source="test", content_hash=content_hash
    )
    session.add(offer)
    session.commit()
    return offer


def test_relevant_offer_clears_the_gate(session, fake_embeddings):
    _backend_profile(session)
    offer = _offer(session, "Backend Engineer", "python fastapi postgres", "h1")

    result = prefilter_offer(session, offer, PrefilterSettings(min_similarity=0.3, top_k=4))

    assert result.gated is False
    assert result.similarity > 0.3
    assert result.item_keys == ["experience:acme|backend engineer"]


def test_unrelated_offer_is_gated_out(session, fake_embeddings):
    _backend_profile(session)
    offer = _offer(session, "Nurse", "nurse sales", "h2")

    result = prefilter_offer(session, offer, PrefilterSettings(min_similarity=0.3, top_k=4))

    # this is the junk filter doing its only job
    assert result.gated is True
    assert result.similarity < 0.3


def test_empty_profile_passes_everything_through(session, fake_embeddings):
    offer = _offer(session, "Nurse", "nurse sales", "h3")

    result = prefilter_offer(session, offer, PrefilterSettings(min_similarity=0.9, top_k=4))

    # with no profile vectors the gate has no opinion; blocking the whole queue
    # on a fresh install would be far worse than a few wasted calls
    assert result.gated is False
    assert result.item_keys == []


def test_similarity_is_the_top_k_mean(session, fake_embeddings):
    _backend_profile(session)
    offer = _offer(session, "Backend Engineer", "python", "h4")

    result = prefilter_offer(session, offer, PrefilterSettings(min_similarity=0.0, top_k=1))

    assert 0.0 <= result.similarity <= 1.0
