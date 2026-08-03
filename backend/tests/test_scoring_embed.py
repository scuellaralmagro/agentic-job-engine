import pytest

from aje.extraction.profile_service import PROFILE_ID, save_profile
from aje.extraction.schema import Achievement, Experience, ProfileData
from aje.models import Embedding, Offer
from aje.scoring import embed as embed_mod
from tests.fakes import FakeEmbeddings


@pytest.fixture
def fake_embeddings(monkeypatch):
    fake = FakeEmbeddings()
    monkeypatch.setattr(embed_mod, "embeddings_for", lambda task: fake)
    return fake


def _save_profile(session, *, title="Backend Engineer"):
    save_profile(
        session,
        ProfileData(
            experiences=[
                Experience(company="Acme", title=title, description="Python and Postgres")
            ],
            achievements=[Achievement(text="Scaled Kubernetes cluster")],
        ),
    )


def test_vector_packing_roundtrips():
    values = [0.5, -0.25, 1.0]
    assert embed_mod.unpack_vector(embed_mod.pack_vector(values)) == pytest.approx(values)


def test_profile_items_are_embedded_and_stored(session, fake_embeddings):
    _save_profile(session)

    count = embed_mod.ensure_profile_embeddings(session)

    assert count == 2
    rows = session.query(Embedding).filter_by(owner_kind="profile_item").all()
    keys = {r.item_key for r in rows}
    assert "experience:acme|backend engineer" in keys
    assert any(k.startswith("achievement:") for k in keys)
    assert all(r.owner_id == PROFILE_ID for r in rows)
    assert all(r.dim == len(fake_embeddings.embed_query("x")) for r in rows)


def test_unchanged_items_are_not_re_embedded(session, fake_embeddings):
    _save_profile(session)
    embed_mod.ensure_profile_embeddings(session)
    embedded_after_first = len(fake_embeddings.embedded_texts)

    count = embed_mod.ensure_profile_embeddings(session)

    assert count == 0
    # re-running a scoring pass must not cost a single embedding call
    assert len(fake_embeddings.embedded_texts) == embedded_after_first


def test_changed_items_are_re_embedded_and_stale_ones_removed(session, fake_embeddings):
    _save_profile(session, title="Backend Engineer")
    embed_mod.ensure_profile_embeddings(session)

    _save_profile(session, title="Staff Engineer")
    count = embed_mod.ensure_profile_embeddings(session)

    keys = {r.item_key for r in session.query(Embedding).filter_by(owner_kind="profile_item")}
    assert count == 1
    assert "experience:acme|staff engineer" in keys
    assert "experience:acme|backend engineer" not in keys


def test_offer_embeddings_are_stored_and_returned(session, fake_embeddings):
    offer = Offer(
        title="Backend Engineer",
        company="Acme",
        location="Madrid",
        description="Python and FastAPI",
        source="test",
        content_hash="h1",
    )
    session.add(offer)
    session.commit()

    vectors = embed_mod.ensure_offer_embeddings(session, offer, chunk_chars=800)

    assert len(vectors) == 2  # title + one chunk
    rows = session.query(Embedding).filter_by(owner_kind="offer", owner_id=offer.id).all()
    assert {r.item_key for r in rows} == {"title", "chunk:0"}


def test_rebuild_clears_and_re_embeds_profile_items(session, fake_embeddings):
    _save_profile(session)
    embed_mod.ensure_profile_embeddings(session)
    before = len(fake_embeddings.embedded_texts)

    count = embed_mod.rebuild_all_embeddings(session)

    assert count == 2
    assert len(fake_embeddings.embedded_texts) == before + 2
