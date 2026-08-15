from fastapi.testclient import TestClient

from aje.api.profile import get_db_session
from aje.app import create_app
from aje.discovery import graph as graph_mod
from aje.discovery import manual as manual_mod
from aje.models import DiscoveryRun, Offer, SavedSearch


def _client(session):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    return TestClient(app)


def test_saved_search_crud(session):
    client = _client(session)

    created = client.post(
        "/searches",
        json={
            "name": "Python Madrid",
            "query": "python",
            "filters": {"locations": ["Madrid"]},
            "schedule": "0 8 * * *",
        },
    )
    assert created.status_code == 200
    search_id = created.json()["id"]

    assert len(client.get("/searches").json()) == 1

    updated = client.put(
        f"/searches/{search_id}",
        json={"name": "Python Remoto", "query": "python", "filters": {}},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Python Remoto"
    assert updated.json()["schedule"] is None

    assert client.delete(f"/searches/{search_id}").status_code == 200
    assert client.get("/searches").json() == []


def test_a_search_saved_without_a_cap_gets_the_default(session):
    """The Pydantic default carries this, not the column: create_search does
    SavedSearch(**body.model_dump()), so a None default would override the column
    default and every new search would be born uncapped."""
    client = _client(session)

    created = client.post(
        "/searches", json={"name": "s", "query": "python", "filters": {}}
    )

    assert created.status_code == 200
    assert created.json()["max_offers"] == 25


def test_an_explicit_null_cap_means_uncapped(session):
    """Also guards the model: SQLAlchemy applies a column default whenever the value
    is None at INSERT and cannot tell "explicitly None" from "unset", so putting
    default=25 back on SavedSearch.max_offers would swallow this and fail here."""
    client = _client(session)

    created = client.post(
        "/searches",
        json={"name": "s", "query": "python", "filters": {}, "max_offers": None},
    )

    assert created.status_code == 200
    assert created.json()["max_offers"] is None


def test_a_zero_or_negative_cap_is_rejected(session):
    client = _client(session)

    for bad in (0, -5):
        resp = client.post(
            "/searches",
            json={"name": "s", "query": "python", "filters": {}, "max_offers": bad},
        )
        assert resp.status_code == 422


def test_update_missing_search_returns_404(session):
    client = _client(session)
    resp = client.put("/searches/999", json={"name": "x", "query": "y", "filters": {}})
    assert resp.status_code == 404


def test_run_search_returns_a_queued_run_record(session, monkeypatch):
    """Run-now is asynchronous now: it hands back a run to watch, not a result."""
    from aje.discovery import jobs as jobs_mod

    saved = SavedSearch(name="s", query="python", filters={"location": "Madrid"})
    session.add(saved)
    session.commit()

    enqueued: list[int] = []
    monkeypatch.setattr(
        jobs_mod, "enqueue_run", lambda rid, cap=None: enqueued.append(rid)
    )

    resp = _client(session).post(f"/searches/{saved.id}/run")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"
    assert body["kind"] == "scheduled"
    assert body["term"] == "python"
    assert body["filters"] == {"location": "Madrid"}
    assert body["saved_search_id"] == saved.id
    assert enqueued == [body["id"]]


def test_run_now_on_a_saved_search_applies_its_cap(session, monkeypatch):
    """Run-now was uncapped too: it called enqueue_run with no cap argument."""
    from aje.discovery import jobs as jobs_mod

    saved = SavedSearch(name="s", query="python", filters={}, max_offers=25)
    session.add(saved)
    session.commit()

    enqueued: list[tuple[int, int | None]] = []
    monkeypatch.setattr(
        jobs_mod, "enqueue_run", lambda rid, cap=None: enqueued.append((rid, cap))
    )

    resp = _client(session).post(f"/searches/{saved.id}/run")

    assert resp.status_code == 200
    assert enqueued == [(resp.json()["id"], 25)]


def test_run_missing_search_returns_404(session):
    assert _client(session).post("/searches/999/run").status_code == 404


def test_list_runs_and_get_one(session):
    session.add(DiscoveryRun(status="partial", offers_found=1, offers_new=1))
    session.commit()
    client = _client(session)

    runs = client.get("/runs").json()
    assert len(runs) == 1 and runs[0]["status"] == "partial"

    assert client.get(f"/runs/{runs[0]['id']}").status_code == 200
    assert client.get("/runs/999").status_code == 404


def test_list_offers_paginates(session):
    for i in range(3):
        session.add(
            Offer(title=f"Job {i}", source="stub", content_hash=f"h{i}", url="https://x")
        )
    session.commit()

    offers = _client(session).get("/offers?limit=2").json()
    assert len(offers) == 2
    assert "title" in offers[0] and "content_hash" not in offers[0]


def test_import_offer_endpoint(session, monkeypatch):
    def fake_import(sess, *, text=None, url=None):
        offer = Offer(
            title="Imported", source="manual", content_hash="mh", url="https://x/1"
        )
        sess.add(offer)
        sess.commit()
        return offer

    monkeypatch.setattr(manual_mod, "import_offer", fake_import)

    resp = _client(session).post("/offers/import", json={"text": "a job"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Imported"


def test_import_offer_without_text_or_url_returns_400(session):
    resp = _client(session).post("/offers/import", json={})
    assert resp.status_code == 400


def test_offers_list_includes_description_seniority_and_skills(session):
    session.add(
        Offer(
            title="Data Engineer",
            company="Acme",
            source="test",
            content_hash="offer-desc-1",
            skills=["python", "sql"],
            seniority="senior",
            description="Full description here.",
        )
    )
    session.commit()

    body = _client(session).get("/offers").json()

    row = next(o for o in body if o["title"] == "Data Engineer")
    assert row["description"] == "Full description here."
    assert row["seniority"] == "senior"
    assert row["skills"] == ["python", "sql"]


def test_post_runs_returns_immediately_in_running_state(session, monkeypatch):
    from aje.api import discovery as discovery_api

    enqueued: list[tuple[int, int | None]] = []
    monkeypatch.setattr(
        discovery_api, "enqueue_run", lambda rid, cap=None: enqueued.append((rid, cap))
    )

    body = (
        _client(session)
        .post("/runs", json={"term": "python madrid", "max_offers": 20})
        .json()
    )

    assert body["status"] == "running"
    assert body["term"] == "python madrid"
    assert body["kind"] == "manual"
    assert body["finished_at"] is None
    assert enqueued == [(body["id"], 20)]


def test_post_runs_rejects_a_blank_term(session):
    assert _client(session).post("/runs", json={"term": "  "}).status_code == 400


def test_run_now_is_asynchronous_and_refuses_a_concurrent_run(session, monkeypatch):
    from aje.discovery import jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "enqueue_run", lambda rid, cap=None: None)
    saved = SavedSearch(name="s", query="python", filters={})
    session.add(saved)
    session.commit()

    client = _client(session)
    first = client.post(f"/searches/{saved.id}/run")
    assert first.status_code == 200 and first.json()["status"] == "running"

    # a cron tick landing on a manual run-now would otherwise double-charge
    assert client.post(f"/searches/{saved.id}/run").status_code == 409


def test_run_results_include_the_offer_and_its_match(session):
    from aje.discovery import jobs as jobs_mod
    from aje.discovery import results as results_mod
    from aje.models import Match

    run = jobs_mod.create_run(session, term="python", filters={}, kind="manual")
    offer = Offer(title="Backend Engineer", source="test", content_hash="r1", skills=[])
    session.add(offer)
    session.commit()
    results_mod.record_result(
        session, run_id=run.id, offer_id=offer.id, is_new=True, status="scored"
    )
    session.add(
        Match(
            offer_id=offer.id,
            profile_id=1,
            fitness=82.0,
            scored_by="rubric",
            above_threshold=True,
            status="new",
        )
    )
    session.commit()

    body = _client(session).get(f"/runs/{run.id}/results").json()

    assert len(body) == 1
    assert body[0]["status"] == "scored" and body[0]["is_new"] is True
    assert body[0]["offer"]["title"] == "Backend Engineer"
    assert body[0]["match"]["fitness"] == 82.0


def test_estimate_reports_a_ceiling(session):
    body = _client(session).get("/runs/estimate").json()

    assert body["max_offers"] > 0
    assert body["max_cost_usd"] == round(
        body["max_offers"] * body["cost_per_offer_usd"], 2
    )
