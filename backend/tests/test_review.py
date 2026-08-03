import pytest

from aje.models import Match, Offer
from aje.scoring import review


def _scored_offer(
    session, *, title, fitness, above=True, scored_by="rubric", status="new", h
):
    offer = Offer(title=title, source="test", content_hash=h, skills=[])
    session.add(offer)
    session.commit()
    session.add(
        Match(
            offer_id=offer.id,
            profile_id=1,
            fitness=fitness,
            above_threshold=above,
            scored_by=scored_by,
            status=status,
        )
    )
    session.commit()
    return offer


def test_queue_returns_above_threshold_rubric_matches_best_first(session):
    _scored_offer(session, title="A", fitness=70.0, h="h1")
    _scored_offer(session, title="B", fitness=90.0, h="h2")

    queue = review.list_queue(session)

    assert [m.fitness for m in queue] == [90.0, 70.0]


def test_queue_excludes_below_threshold_and_vector_only_matches(session):
    _scored_offer(session, title="Good", fitness=80.0, h="h1")
    _scored_offer(session, title="Weak", fitness=40.0, above=False, h="h2")
    # a vector fitness is not on the same scale as a rubric one and must never
    # be ranked beside it
    _scored_offer(
        session, title="Junk", fitness=95.0, above=False, scored_by="vector", h="h3"
    )

    assert [m.fitness for m in review.list_queue(session)] == [80.0]


def test_queue_filters_by_status_and_min_fitness(session):
    _scored_offer(session, title="A", fitness=70.0, h="h1")
    _scored_offer(session, title="B", fitness=90.0, status="accepted", h="h2")

    assert len(review.list_queue(session, status="accepted")) == 1
    assert review.list_queue(session, min_fitness=80.0) == []


def test_set_status_transitions_a_match(session):
    offer = _scored_offer(session, title="A", fitness=70.0, h="h1")
    match_id = session.query(Match).one().id

    updated = review.set_status(session, match_id, "accepted")

    assert updated.status == "accepted"
    assert offer.id == updated.offer_id


def test_unknown_status_is_rejected(session):
    _scored_offer(session, title="A", fitness=70.0, h="h1")
    match_id = session.query(Match).one().id

    with pytest.raises(ValueError, match="unknown status"):
        review.set_status(session, match_id, "maybe")
