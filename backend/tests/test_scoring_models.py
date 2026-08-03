import pytest
from sqlalchemy.exc import IntegrityError

from aje.models import Embedding, Match, Offer


def _offer(session, title="Backend Engineer", content_hash="h1"):
    offer = Offer(title=title, source="test", content_hash=content_hash, skills=[])
    session.add(offer)
    session.commit()
    return offer


def test_embedding_roundtrips_a_blob(session):
    session.add(
        Embedding(
            owner_kind="profile_item",
            owner_id=1,
            item_key="experience:acme|backend-engineer",
            text_hash="abc",
            dim=4,
            vector=b"\x00\x01\x02\x03",
        )
    )
    session.commit()

    row = session.query(Embedding).one()
    assert row.vector == b"\x00\x01\x02\x03"
    assert row.dim == 4


def test_embedding_owner_item_key_is_unique(session):
    for _ in range(2):
        session.add(
            Embedding(
                owner_kind="offer",
                owner_id=7,
                item_key="chunk:0",
                text_hash="abc",
                dim=4,
                vector=b"\x00",
            )
        )
    with pytest.raises(IntegrityError):
        session.commit()


def test_match_defaults_to_new_and_records_how_it_was_scored(session):
    offer = _offer(session)
    match = Match(
        offer_id=offer.id, profile_id=1, fitness=72.5, scored_by="rubric", similarity=0.41
    )
    session.add(match)
    session.commit()

    row = session.query(Match).one()
    assert row.status == "new"
    assert row.scored_by == "rubric"
    assert row.similarity == pytest.approx(0.41)


def test_one_match_per_offer_and_profile(session):
    offer = _offer(session)
    for _ in range(2):
        session.add(Match(offer_id=offer.id, profile_id=1, fitness=50.0))
    with pytest.raises(IntegrityError):
        session.commit()


def test_sqlite_vec_is_available_to_the_test_session(session):
    # the whole prefilter depends on this function existing on every connection
    from sqlalchemy import text

    assert session.execute(text("SELECT vec_version()")).scalar_one()
