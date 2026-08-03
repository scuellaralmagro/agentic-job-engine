from aje.adaptation.persist import save_projection
from aje.adaptation.schema import (
    AdaptationResult,
    Suggestion,
    TailoredBullet,
    TailoredCv,
    TailoredExperience,
)
from aje.models import CvProjection, Match, Offer


def _offer(session) -> Offer:
    offer = Offer(
        title="Senior Backend Engineer",
        company="Globex",
        source="test",
        content_hash="h1",
        skills=[],
    )
    session.add(offer)
    session.commit()
    return offer


def _match(session, offer) -> Match:
    match = Match(offer_id=offer.id, profile_id=1, fitness=78.0, status="accepted")
    session.add(match)
    session.commit()
    return match


def _result() -> AdaptationResult:
    return AdaptationResult(
        cv=TailoredCv(
            language="en",
            headline="Backend Engineer",
            summary="Builds APIs.",
            experiences=[
                TailoredExperience(
                    source_key="experience:acme|backend engineer",
                    bullets=[
                        TailoredBullet(
                            source_key="experience:acme|backend engineer#bullet:0",
                            text="Cut p99 latency 40%",
                        )
                    ],
                )
            ],
            skill_keys=["skill:python"],
        ),
        suggestions=[
            Suggestion(
                kind="rewrite",
                source_key="experience:acme|backend engineer#bullet:0",
                before="Worked on the API",
                after="Cut p99 latency 40%",
                reason="The offer leads with performance",
            )
        ],
    )


def test_a_projection_records_content_suggestions_and_language(session):
    offer = _offer(session)
    match = _match(session, offer)

    projection = save_projection(session, match, _result())

    assert projection.id is not None
    assert projection.match_id == match.id
    assert projection.offer_id == offer.id
    assert projection.language == "en"
    assert projection.content_json["headline"] == "Backend Engineer"
    assert projection.suggestions[0]["kind"] == "rewrite"


def test_the_projection_is_named_after_the_offer(session):
    offer = _offer(session)
    match = _match(session, offer)

    projection = save_projection(session, match, _result())

    assert "Senior Backend Engineer" in projection.name
    assert "Globex" in projection.name


def test_regenerating_inserts_a_second_row_rather_than_overwriting(session):
    offer = _offer(session)
    match = _match(session, offer)

    first = save_projection(session, match, _result())
    second = save_projection(session, match, _result())

    assert first.id != second.id
    assert session.query(CvProjection).count() == 2
