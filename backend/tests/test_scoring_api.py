from fastapi.testclient import TestClient

from aje.api import scoring as scoring_api
from aje.api.profile import get_db_session
from aje.app import create_app
from aje.models import Match, Offer
from aje.scoring.schema import ScoringSummary


def _client(session):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    return TestClient(app)


def _match(session, *, title, fitness, above=True, scored_by="rubric", h):
    offer = Offer(title=title, company="Acme", source="test", content_hash=h, skills=[])
    session.add(offer)
    session.commit()
    match = Match(
        offer_id=offer.id,
        profile_id=1,
        fitness=fitness,
        above_threshold=above,
        scored_by=scored_by,
        rubric={"skills": {"score": 80, "evidence": "Python"}},
        gaps=[{"requirement": "Kubernetes", "severity": "minor"}],
        explanation="Good fit.",
    )
    session.add(match)
    session.commit()
    return match


def test_queue_lists_matches_with_their_offer(session):
    _match(session, title="Backend Engineer", fitness=88.0, h="h1")

    body = _client(session).get("/queue").json()

    assert len(body) == 1
    assert body[0]["fitness"] == 88.0
    assert body[0]["offer"]["title"] == "Backend Engineer"


def test_queue_honours_min_fitness(session):
    _match(session, title="A", fitness=70.0, h="h1")

    assert _client(session).get("/queue", params={"min_fitness": 80}).json() == []


def test_match_detail_returns_the_rubric_and_gaps(session):
    match = _match(session, title="A", fitness=70.0, h="h1")

    body = _client(session).get(f"/matches/{match.id}").json()

    assert body["rubric"]["skills"]["score"] == 80
    assert body["gaps"][0]["requirement"] == "Kubernetes"
    assert body["explanation"] == "Good fit."


def test_missing_match_is_404(session):
    assert _client(session).get("/matches/999").status_code == 404


def test_accept_and_dismiss_change_status(session):
    match = _match(session, title="A", fitness=70.0, h="h1")
    client = _client(session)

    assert client.post(f"/matches/{match.id}/accept").json()["status"] == "accepted"
    assert client.post(f"/matches/{match.id}/dismiss").json()["status"] == "dismissed"
    assert client.get("/queue").json() == []


def test_score_endpoint_delegates_to_the_graph(session, monkeypatch):
    calls = {}

    def _fake(sess, offer_ids, *, rescore=False):
        calls["ids"] = offer_ids
        calls["rescore"] = rescore
        return ScoringSummary(scored=len(offer_ids))

    monkeypatch.setattr(scoring_api, "score_offers", _fake)

    body = _client(session).post("/score", json={"offer_ids": [1, 2], "rescore": True}).json()

    assert body["scored"] == 2
    assert calls == {"ids": [1, 2], "rescore": True}


def test_score_with_an_empty_body_backfills(session, monkeypatch):
    calls = {}

    def _fake(sess, *, since=None, rescore=False):
        calls["since"] = since
        return ScoringSummary(scored=3)

    monkeypatch.setattr(scoring_api, "score_all_unscored", _fake)

    assert _client(session).post("/score", json={}).json()["scored"] == 3
    assert calls["since"] is None


def test_embeddings_rebuild_reports_how_many_were_rebuilt(session, monkeypatch):
    monkeypatch.setattr(scoring_api, "rebuild_all_embeddings", lambda sess: 4)

    assert _client(session).post("/embeddings/rebuild").json() == {"embedded": 4}


def test_queue_offer_payload_includes_description_and_created_at(session):
    match = _match(session, title="A", fitness=70.0, h="h1")
    offer = session.get(Offer, match.offer_id)
    offer.description = "We need a Python engineer."
    session.commit()

    body = _client(session).get("/queue").json()

    assert body[0]["offer"]["description"] == "We need a Python engineer."
    assert body[0]["offer"]["created_at"] is not None


def test_reset_returns_match_to_queue(session):
    match = _match(session, title="A", fitness=70.0, h="h1")
    client = _client(session)

    client.post(f"/matches/{match.id}/dismiss")
    assert client.get("/queue").json() == []

    assert client.post(f"/matches/{match.id}/reset").json()["status"] == "new"
    assert len(client.get("/queue").json()) == 1
