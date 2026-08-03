from aje.models import Match, Offer
from aje.scoring.persist import enrich_offer, upsert_rubric_match, upsert_vector_match
from aje.scoring.schema import DimensionScore, Gap, OfferRequirements, RubricResult


def _offer(session, content_hash="h1"):
    offer = Offer(
        title="Backend Engineer", source="test", content_hash=content_hash, skills=[]
    )
    session.add(offer)
    session.commit()
    return offer


def _rubric(skills=80):
    return RubricResult(
        skills=DimensionScore(score=skills, evidence="Python"),
        seniority=DimensionScore(score=70, evidence=""),
        domain=DimensionScore(score=60, evidence=""),
        language=DimensionScore(score=90, evidence=""),
        gaps=[Gap(requirement="Kubernetes", severity="minor")],
        requirements=OfferRequirements(skills=["Python", "FastAPI"], seniority="senior"),
        explanation="Good fit.",
    )


def test_rubric_match_stores_the_breakdown(session):
    offer = _offer(session)

    match = upsert_rubric_match(
        session, offer, _rubric(), fitness=75.0, above_threshold=True, similarity=0.42
    )

    assert match.fitness == 75.0
    assert match.scored_by == "rubric"
    assert match.above_threshold is True
    assert match.similarity == 0.42
    assert match.rubric["skills"]["score"] == 80
    assert match.gaps[0]["requirement"] == "Kubernetes"
    assert match.explanation == "Good fit."
    assert match.scored_at is not None


def test_vector_match_never_enters_the_queue(session):
    offer = _offer(session)

    match = upsert_vector_match(session, offer, similarity=0.12)

    assert match.scored_by == "vector"
    assert match.above_threshold is False
    assert match.rubric == {}
    # the similarity scaled to 0-100 so vector rows still sort sensibly among
    # themselves — it is NOT comparable to a rubric fitness
    assert match.fitness == 12.0


def test_rescoring_updates_in_place(session):
    offer = _offer(session)
    upsert_rubric_match(
        session, offer, _rubric(80), fitness=75.0, above_threshold=True, similarity=0.4
    )

    upsert_rubric_match(
        session, offer, _rubric(40), fitness=55.0, above_threshold=False, similarity=0.4
    )

    assert session.query(Match).count() == 1
    assert session.query(Match).one().fitness == 55.0


def test_rescoring_preserves_the_users_decision(session):
    offer = _offer(session)
    match = upsert_rubric_match(
        session, offer, _rubric(), fitness=75.0, above_threshold=True, similarity=0.4
    )
    match.status = "accepted"
    session.commit()

    upsert_rubric_match(
        session, offer, _rubric(40), fitness=55.0, above_threshold=False, similarity=0.4
    )

    assert session.query(Match).one().status == "accepted"


def test_enrichment_fills_the_columns_discovery_left_empty(session):
    offer = _offer(session)

    enrich_offer(session, offer, _rubric().requirements)

    refreshed = session.get(Offer, offer.id)
    assert refreshed.skills == ["Python", "FastAPI"]
    assert refreshed.seniority == "senior"


def test_enrichment_does_not_blank_existing_values(session):
    offer = _offer(session)
    offer.skills = ["Go"]
    offer.seniority = "mid"
    session.commit()

    enrich_offer(session, offer, OfferRequirements(skills=[], seniority=None))

    refreshed = session.get(Offer, offer.id)
    assert refreshed.skills == ["Go"]
    assert refreshed.seniority == "mid"
