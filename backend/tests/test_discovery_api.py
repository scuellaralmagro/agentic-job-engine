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


def test_update_missing_search_returns_404(session):
    client = _client(session)
    resp = client.put("/searches/999", json={"name": "x", "query": "y", "filters": {}})
    assert resp.status_code == 404


def test_run_search_returns_run_record(session, monkeypatch):
    saved = SavedSearch(name="s", query="python", filters={})
    session.add(saved)
    session.commit()

    def fake_run(sess, saved_search_id):
        run = DiscoveryRun(
            saved_search_id=saved_search_id,
            status="ok",
            offers_found=3,
            offers_new=2,
            source_results=[{"source": "stub", "count": 3, "error": None}],
        )
        sess.add(run)
        sess.commit()
        return run

    monkeypatch.setattr(graph_mod, "run_saved_search", fake_run)

    resp = _client(session).post(f"/searches/{saved.id}/run")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok" and body["offers_new"] == 2
    assert body["source_results"][0]["source"] == "stub"


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
